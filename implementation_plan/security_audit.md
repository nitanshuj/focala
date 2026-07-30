# FoCala Security Audit Report

> Audited: Backend (`focala/`) · Frontend (`focala_frontend/`) · Date: 2026-07-30

---

## 🔴 Critical

### C1 — JWT Signature Verification Bypassed (`app/utils/auth.py`)

**File**: [auth.py](file:///c:/Products-Projects/FoCala/code/focala/app/utils/auth.py#L19-L33)

```python
# If secret verification failed, attempt unverified decode for Supabase tokens
payload = jwt.get_unverified_claims(token)   # ← DANGEROUS
```

The token verification logic first tries to verify with `JWT_SECRET`, but if that **fails** (e.g., due to mismatched secret), it **silently falls back to reading the token without verifying the signature at all**. Any attacker can craft an arbitrary JWT with any `sub` (user ID) claim and it will be accepted as valid.

**Fix**: On JWTError after signature check, return `None` — never accept unverified tokens.

```python
if settings.JWT_SECRET:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
    # Remove the fallback to get_unverified_claims
else:
    payload = jwt.get_unverified_claims(token)   # only if no secret at all (dev-only)
```

---

### C2 — Unauthenticated Requests Fall Through to a Shared "Dev" UUID (`app/dependencies.py`)

**File**: [dependencies.py](file:///c:/Products-Projects/FoCala/code/focala/app/dependencies.py#L11-L13)

```python
if not credentials:
    # For testing / unauthenticated dev fallback if needed
    return "00000000-0000-0000-0000-000000000000"
```

Any request with **no `Authorization` header** returns the hardcoded dev UUID instead of rejecting. In production, this means an anonymous caller gets full access to that UUID's data. The same default ID is returned in multiple error paths in `utils/auth.py` (lines 30, 33, 36).

**Fix**: Raise `HTTP_401_UNAUTHORIZED` when no credentials are provided. Remove all hardcoded fallback UUID returns; only allow it behind a `DEBUG` environment flag.

---

### C3 — Dev Tokens Bypass Authentication (`app/utils/auth.py` L15-17)

**File**: [auth.py](file:///c:/Products-Projects/FoCala/code/focala/app/utils/auth.py#L15-L17)

```python
if token.startswith("dev-"):
    return "00000000-0000-0000-0000-000000000000"
```

Any string starting with `dev-` (e.g., `dev-anything`) is silently accepted as a valid authenticated token. There is no environment guard preventing this from running in production. The auth API itself issues `dev-jwt-token-*` tokens freely.

**Fix**: Gate this branch behind an explicit `DEBUG=true` env variable check.

---

## 🔴 High

### H1 — Overly Permissive CORS: `allow_origins=["*"]` with `allow_credentials=True` (`app/main.py`)

**File**: [main.py](file:///c:/Products-Projects/FoCala/code/focala/app/main.py#L29-L35)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ← wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This combination is **invalid per the CORS spec** — browsers reject `allow_credentials=True` when origin is `*`. More critically, it signals intent to allow cookies/auth headers from any origin. When fixed to a real origin list, it should be locked to the production Netlify domain only.

**Fix**:
```python
allow_origins = os.getenv("ALLOWED_ORIGINS", "https://your-app.netlify.app").split(",")
app.add_middleware(CORSMiddleware, allow_origins=allow_origins, allow_credentials=True, ...)
```

---

### H2 — Google Calendar OAuth Callback: XSS via Unescaped `google_email` in HTML Response (`app/api/calendar.py`)

**File**: [calendar.py](file:///c:/Products-Projects/FoCala/code/focala/app/api/calendar.py#L73-L79)

```python
html_content = f"""
  ...
  <p>Account <strong>{result.get('google_email', '')}</strong> has been linked...</p>
  <script>
    window.opener.postMessage({"email": "{result.get('google_email', '')}"} , "*");
  </script>
"""
```

The `google_email` value from the OAuth token exchange is injected **directly into an HTML string without escaping**. A malicious OAuth provider (or MITM) returning `email": alert(1)//` would execute arbitrary JavaScript. The `postMessage` origin is also `"*"` — it should be locked to the frontend origin.

**Fix**: Use `html.escape()` on `google_email`, and restrict `postMessage` target origin.

---

### H3 — `postMessage` Sends to `"*"` (Any Origin) (`app/api/calendar.py` L79)

```python
window.opener.postMessage({...}, "*");
```

Any page that opened the OAuth popup can receive this message including attacker-controlled pages, potentially leaking the Google email. Restrict to the known frontend origin.

---

### H4 — Hardcoded `localhost` Redirect URL in OAuth Callback (`app/api/calendar.py` L61, L75)

```html
<meta http-equiv="refresh" content="2;url=http://localhost:8080/settings?calendar_connected=true" />
<a href="http://localhost:8080/settings?calendar_connected=true">...</a>
```

The redirect after OAuth is hardcoded to `localhost:8080`. In production this will silently fail and users will not return to the app. This should be an environment variable.

---

### H5 — Dev Auth Fallback Returns Successful Auth Responses in Production (`app/api/auth.py`)

**File**: [auth.py](file:///c:/Products-Projects/FoCala/code/focala/app/api/auth.py#L61-L73)

```python
if "placeholder" in settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
    # return fake dev-jwt-token-* token
```

When Supabase is misconfigured or the service key is missing (common in a broken deployment), **login and signup silently succeed** with fake tokens instead of returning an error. This means users could think they're logged into a real account while data is lost.

---

## 🟡 Medium

### M1 — Task `update` Endpoint Does Not Verify Ownership Before Updating (`app/api/tasks.py` L53)

**File**: [tasks.py](file:///c:/Products-Projects/FoCala/code/focala/app/api/tasks.py#L49-L58)

```python
res = supabase.table("tasks").update(data).eq("id", task_id).eq("user_id", user_id).execute()
```

This correctly filters by `user_id`, which is good. However, the `focus.py` endpoint updates `actual_minutes` on a task **without checking ownership**:

```python
# focus.py L32-35
task_res = supabase.table("tasks").select("actual_minutes").eq("id", payload.task_id).execute()
# No .eq("user_id", user_id) check!
supabase.table("tasks").update(...).eq("id", payload.task_id).execute()
```

An authenticated user can log focus time against any other user's task ID, incrementing their `actual_minutes`.

---

### M2 — Brain Dump `triage` Marks Entry as Triaged Without Filtering by `user_id` (`app/api/brain_dump.py` L71)

**File**: [brain_dump.py](file:///c:/Products-Projects/FoCala/code/focala/app/api/brain_dump.py#L71)

```python
supabase.table("brain_dumps").update({"triaged": True}).eq("id", dump_id).execute()
# Missing: .eq("user_id", user_id)
```

The `SELECT` above it checks `user_id`, but the `UPDATE` does not, which is inconsistent and could be exploited if the DB's RLS is ever misconfigured.

---

### M3 — `payload: dict` Accepts Arbitrary Input with No Validation (`app/api/tasks.py`, `app/api/planning.py`)

Several endpoints use raw `dict` as the request body type:

- [`tasks.py` L82-84](file:///c:/Products-Projects/FoCala/code/focala/app/api/tasks.py#L82): `/tasks/breakdown` — `payload: dict`
- [`planning.py` L12-14](file:///c:/Products-Projects/FoCala/code/focala/app/api/planning.py#L12): `/plan/energy` — `payload: dict`

These bypass Pydantic validation entirely, allowing unexpected fields, type coercion issues, or injection of large payloads. Define proper Pydantic models for all request bodies.

---

### M4 — API Key Exposed in Logs (`app/services/gemini_client.py` L40)

```python
logger.info(f"Generating content with Gemini model: {model_name}")
```

While model name alone isn't secret, error messages from Gemini can include API key details or request metadata. The broader pattern of logging exception strings from external services risks leaking secrets in log aggregators. Ensure log redaction is in place in production.

---

### M5 — `JWT_SECRET` Missing from `render.yaml` / Not Enforced as Required

**File**: [render.yaml](file:///c:/Products-Projects/FoCala/code/focala/render.yaml)

`JWT_SECRET` is listed as a `sync: false` env var but there is no startup validation that it's actually set. If omitted, the backend runs with no JWT secret and falls back to `jwt.get_unverified_claims()` for all tokens (see C1/C3).

**Fix**: Add startup validation:
```python
if not settings.JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be set in production")
```

---

### M6 — Sensitive User Data Exported Without Rate Limiting (`app/api/settings.py` L43-58)

**File**: [settings.py](file:///c:/Products-Projects/FoCala/code/focala/app/api/settings.py#L43-L58)

The `/settings/export` endpoint returns **all tasks, routines, mood logs, brain dumps, and plans** in a single response with no pagination or rate limiting. An attacker with a valid session token (including a `dev-` token from C3) can dump all data in one request.

---

## 🟢 Low / Info

### L1 — Token Stored in `localStorage` (Frontend)

**File**: [api.ts](file:///c:/Products-Projects/FoCala/code/focala_frontend/src/lib/api.ts#L12-L17)

```typescript
export const TOKEN_KEY = "focala_token";
window.localStorage.setItem(TOKEN_KEY, token);
```

JWT tokens in `localStorage` are accessible to any JavaScript on the page (XSS risk). `HttpOnly` cookies are the more secure alternative, though they require backend CSRF protection. This is a known tradeoff for SPAs — acceptable if XSS vectors are otherwise mitigated, but worth documenting.

---

### L2 — `console.error(error)` Leaks Full Error Stack in Production (`__root.tsx` L41)

**File**: [__root.tsx](file:///c:/Products-Projects/FoCala/code/focala_frontend/src/routes/__root.tsx#L41)

```tsx
console.error(error);
```

Full error objects including stack traces are logged to the browser console in production. This could expose implementation details. Consider sending these to a structured error logger instead and suppressing raw console output.

---

### L3 — No Content Security Policy (CSP) Headers

Neither `netlify.toml` nor the HTML template define a `Content-Security-Policy` header. This increases XSS risk surface. A strict CSP should be added to `netlify.toml`:

```toml
[[headers]]
  for = "/*"
  [headers.values]
    Content-Security-Policy = "default-src 'self'; script-src 'self'; connect-src 'self' https://your-backend.onrender.com;"
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
```

---

### L4 — `datetime.utcnow()` Deprecation Warning (Python 3.12+)

Multiple files use `datetime.utcnow()` which is deprecated in Python 3.12. While not a security issue, it could cause unexpected behavior in future Python versions. Replace with `datetime.now(timezone.utc)`.

---

## Summary Table

| ID | Severity | Location | Issue |
|----|----------|----------|-------|
| C1 | 🔴 Critical | `utils/auth.py` | JWT signature silently skipped on error |
| C2 | 🔴 Critical | `dependencies.py` | No auth → shared dev UUID, not 401 |
| C3 | 🔴 Critical | `utils/auth.py` | `dev-*` tokens accepted in production |
| H1 | 🔴 High | `main.py` | CORS wildcard + credentials enabled |
| H2 | 🔴 High | `api/calendar.py` | XSS via unescaped email in HTML response |
| H3 | 🔴 High | `api/calendar.py` | postMessage origin `"*"` |
| H4 | 🔴 High | `api/calendar.py` | Hardcoded localhost in OAuth redirect |
| H5 | 🔴 High | `api/auth.py` | Dev fallback auth silently succeeds |
| M1 | 🟡 Medium | `api/focus.py` | Task update lacks ownership check |
| M2 | 🟡 Medium | `api/brain_dump.py` | `triaged` update lacks `user_id` filter |
| M3 | 🟡 Medium | `api/tasks.py`, `planning.py` | Raw `dict` payloads bypass validation |
| M4 | 🟡 Medium | `services/gemini_client.py` | External error details logged |
| M5 | 🟡 Medium | `render.yaml` / config | No `JWT_SECRET` startup enforcement |
| M6 | 🟡 Medium | `api/settings.py` | Bulk data export with no rate limit |
| L1 | 🟢 Low | `lib/api.ts` | JWT in localStorage (XSS exposure) |
| L2 | 🟢 Low | `__root.tsx` | `console.error` in production |
| L3 | 🟢 Low | `netlify.toml` | No CSP / security headers |
| L4 | 🟢 Info | Multiple backend files | `datetime.utcnow()` deprecated |

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "")
    GEMINI_BACKUP_MODEL_NAME: str = os.getenv("GEMINI_BACKUP_MODEL_NAME", "")

    VAPID_PRIVATE_KEY: str = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY: str = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_CLAIMS_EMAIL: str = os.getenv("VAPID_CLAIMS_EMAIL", "admin@focala.app")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")

    # Security: production frontend origin used for CORS and OAuth redirects.
    # Comma-separated list, e.g. "https://focala.netlify.app,https://www.focala.app"
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8080")
    ALLOWED_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:5173").split(",")
        if o.strip()
    ]

    # Set DEBUG=true only in local development. NEVER in production.
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

settings = Settings()


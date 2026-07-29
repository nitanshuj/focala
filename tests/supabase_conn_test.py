import os
from dotenv import load_dotenv
from supabase import create_client

def main():
    # Load environment variables from .env
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    print(f"Testing connection to Supabase URL: {url}")

    if not url or not key:
        print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_KEY is missing in your .env file!")
        return

    try:
        client = create_client(url, key)
        # Query profiles table to verify connection
        response = client.table("profiles").select("count", count="exact").execute()
        print("✅ Supabase connection successful!")
        print(f"Profiles query response: {response.data}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    # running command from root: python tests/supabase_conn_test.py
    main()
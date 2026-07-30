import google.generativeai as genai
from app.config import settings
from app.services.gemini_client import generate_content_with_fallback

def main():
    print("=" * 60)
    print("Testing Google Gemini Models (Primary & Backup Fallback)")
    print("=" * 60)
    
    print(f"API Key Configured: {'Yes' if settings.GEMINI_API_KEY else 'No'}")
    print(f"Primary Model: {settings.GEMINI_MODEL_NAME}")
    print(f"Backup Model:  {settings.GEMINI_BACKUP_MODEL_NAME}")
    print("-" * 60)

    if not settings.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY is missing in .env file.")
        return

    genai.configure(api_key=settings.GEMINI_API_KEY)
    prompt = "What are the 5 best productivity tips for ADHD?"
    print(f"Sending Prompt: '{prompt}'\n")

    try:
        response_text = generate_content_with_fallback(prompt)
        print("Response from Gemini:")
        print(response_text)
    except Exception as e:
        print(f"API Test Error: {e}")

    print("=" * 60)

if __name__ == "__main__":
    main()

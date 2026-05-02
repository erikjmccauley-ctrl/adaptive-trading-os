"""
Run this once to authorize the bot with your Schwab account.

What happens:
  1. Your browser opens to Schwab's login page
  2. Log in and approve the API access
  3. Schwab redirects to https://127.0.0.1 — the page will error (nothing is listening there, that's fine)
  4. Copy the full URL from your browser's address bar and paste it here when prompted
  5. Token saved to schwab_token.json — keep this file secure, never commit it

After this runs successfully, the bot will use real-time Schwab data automatically.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def main():
    api_key    = os.getenv('SCHWAB_API_KEY')
    app_secret = os.getenv('SCHWAB_APP_SECRET')

    if not api_key or not app_secret:
        print("ERROR: Add SCHWAB_API_KEY and SCHWAB_APP_SECRET to your .env file first.")
        sys.exit(1)

    try:
        import schwab
    except ImportError:
        print("ERROR: schwab-py not installed. Run: pip install schwab-py")
        sys.exit(1)

    print("\nOpening Schwab login in your browser...")
    print("After logging in, copy the full redirect URL and paste it here.\n")

    client = schwab.auth.easy_client(
        api_key=api_key,
        app_secret=app_secret,
        callback_url='https://127.0.0.1:8182',
        token_path='schwab_token.json',
        interactive=False,
    )

    # Quick connection test
    print("\nTesting connection...")
    try:
        resp = client.get_quotes(['/MES'])
        data = resp.json()
        if '/MES' in data:
            q = data['/MES']
            last = q.get('quote', {}).get('lastPrice', 'N/A')
            print(f"  MES last price: {last}")
        print("\nAuth successful. schwab_token.json saved.")
        print("The bot will now use real-time data automatically.")
    except Exception as e:
        print(f"\nAuth saved but test quote failed: {e}")
        print("This may be normal if markets are closed. Try running main.py.")


if __name__ == '__main__':
    main()

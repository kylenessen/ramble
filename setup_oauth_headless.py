#!/usr/bin/env python3
"""
Dropbox OAuth 2.0 Headless Setup Utility

This script helps you obtain a refresh token for servers without a browser (SSH-only).
You'll need to complete the OAuth flow on your local machine, then use the authorization code here.

Prerequisites:
1. Create a Dropbox app at https://www.dropbox.com/developers/apps
2. Set a redirect URI (can be anything, like https://example.com/auth)
3. Get your app key and app secret from the app settings

Usage:
    1. Run this script to get the authorization URL
    2. Visit the URL in your browser and authorize the app
    3. Copy the authorization code from the redirect URL
    4. Run the script again with the code to get your refresh token

    python setup_oauth_headless.py --app-key YOUR_APP_KEY --app-secret YOUR_APP_SECRET
    python setup_oauth_headless.py --app-key YOUR_APP_KEY --app-secret YOUR_APP_SECRET --auth-code YOUR_AUTH_CODE
"""

import argparse
import json
import urllib.parse
import urllib.request
import sys


def generate_auth_url(app_key: str, redirect_uri: str = "https://example.com/auth") -> str:
    """Generate the authorization URL for manual OAuth flow"""
    
    auth_url = "https://www.dropbox.com/oauth2/authorize?" + urllib.parse.urlencode({
        'client_id': app_key,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'token_access_type': 'offline'  # This is crucial for getting refresh token
    })
    
    return auth_url


def exchange_code_for_tokens(app_key: str, app_secret: str, auth_code: str, redirect_uri: str = "https://example.com/auth") -> dict:
    """Exchange authorization code for access and refresh tokens"""
    
    # Prepare request
    data = urllib.parse.urlencode({
        'code': auth_code,
        'grant_type': 'authorization_code',
        'client_id': app_key,
        'client_secret': app_secret,
        'redirect_uri': redirect_uri
    }).encode()
    
    # Make request
    req = urllib.request.Request(
        'https://api.dropbox.com/oauth2/token',
        data=data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode())
            return response_data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise Exception(f"Token exchange failed: {error_body}")


def main():
    parser = argparse.ArgumentParser(description='Setup Dropbox OAuth 2.0 refresh token (headless)')
    parser.add_argument('--app-key', required=True, help='Dropbox app key')
    parser.add_argument('--app-secret', required=True, help='Dropbox app secret')
    parser.add_argument('--auth-code', help='Authorization code from OAuth flow')
    parser.add_argument('--redirect-uri', default='https://example.com/auth', 
                       help='Redirect URI (must match your app settings)')
    
    args = parser.parse_args()
    
    try:
        if not args.auth_code:
            # Step 1: Generate authorization URL
            print("=== Dropbox OAuth 2.0 Setup (Headless) ===")
            print("Step 1: Get Authorization Code")
            print()
            
            auth_url = generate_auth_url(args.app_key, args.redirect_uri)
            
            print("1. Visit this URL in your browser:")
            print(f"   {auth_url}")
            print()
            print("2. Authorize the application")
            print("3. You'll be redirected to a URL that looks like:")
            print(f"   {args.redirect_uri}?code=AUTHORIZATION_CODE&state=...")
            print()
            print("4. Copy the 'code' parameter from the URL")
            print("5. Run this script again with the code:")
            print(f"   python {sys.argv[0]} --app-key {args.app_key} --app-secret {args.app_secret} --auth-code YOUR_CODE")
            print()
            print("Note: The authorization code expires quickly, so complete step 5 promptly!")
            
        else:
            # Step 2: Exchange code for tokens
            print("=== Dropbox OAuth 2.0 Setup (Headless) ===")
            print("Step 2: Exchange Code for Refresh Token")
            print()
            print("Exchanging authorization code for tokens...")
            
            tokens = exchange_code_for_tokens(args.app_key, args.app_secret, args.auth_code, args.redirect_uri)
            
            print()
            print("=== SUCCESS ===")
            print("Your Dropbox OAuth credentials:")
            print()
            print(f"App Key: {args.app_key}")
            print(f"App Secret: {args.app_secret}")
            print(f"Refresh Token: {tokens['refresh_token']}")
            print()
            print("Add these to your config.yaml:")
            print()
            print("dropbox:")
            print(f"  app_key: \"{args.app_key}\"")
            print(f"  app_secret: \"{args.app_secret}\"")
            print(f"  refresh_token: \"{tokens['refresh_token']}\"")
            print("  root_folder: \"/ramble\"")
            print()
            print("Or set as environment variables:")
            print(f"export DROPBOX_APP_KEY=\"{args.app_key}\"")
            print(f"export DROPBOX_APP_SECRET=\"{args.app_secret}\"")
            print(f"export DROPBOX_REFRESH_TOKEN=\"{tokens['refresh_token']}\"")
            print()
            print("⚠️  Keep these credentials secure and don't commit them to version control!")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
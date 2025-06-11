#!/usr/bin/env python3
"""
Dropbox OAuth 2.0 Setup Utility

This script helps you obtain a refresh token for long-term Dropbox access.
Run this once to get your refresh token, then add it to your config.yaml.

Prerequisites:
1. Create a Dropbox app at https://www.dropbox.com/developers/apps
2. Set the redirect URI to http://localhost:8080/auth (for this script)
3. Get your app key and app secret from the app settings

Usage:
    python setup_oauth.py --app-key YOUR_APP_KEY --app-secret YOUR_APP_SECRET
"""

import argparse
import base64
import json
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import sys
import threading
import time


class AuthHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback"""
    
    def __init__(self, *args, **kwargs):
        self.auth_code = None
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET request from Dropbox OAuth callback"""
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/auth':
            query_params = parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                # Store the authorization code
                self.server.auth_code = query_params['code'][0]
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <head><title>Authorization Successful</title></head>
                <body>
                    <h1>Success!</h1>
                    <p>You can close this window. The authorization code has been received.</p>
                    <script>setTimeout(function(){window.close();}, 3000);</script>
                </body>
                </html>
                ''')
            elif 'error' in query_params:
                error = query_params['error'][0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f'''
                <html>
                <head><title>Authorization Failed</title></head>
                <body>
                    <h1>Error</h1>
                    <p>Authorization failed: {error}</p>
                </body>
                </html>
                '''.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress log messages"""
        pass


def get_authorization_code(app_key: str, redirect_uri: str = "http://localhost:8080/auth") -> str:
    """Get authorization code via OAuth flow"""
    
    # Start local server for callback
    server = HTTPServer(('localhost', 8080), AuthHandler)
    server.auth_code = None
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    # Build authorization URL
    auth_url = "https://www.dropbox.com/oauth2/authorize?" + urllib.parse.urlencode({
        'client_id': app_key,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'token_access_type': 'offline'  # This is crucial for getting refresh token
    })
    
    print(f"Opening browser for authorization...")
    print(f"If the browser doesn't open automatically, visit: {auth_url}")
    
    # Open browser
    webbrowser.open(auth_url)
    
    # Wait for callback
    print("Waiting for authorization...")
    timeout = 300  # 5 minutes
    start_time = time.time()
    
    while server.auth_code is None and (time.time() - start_time) < timeout:
        time.sleep(1)
    
    server.shutdown()
    
    if server.auth_code is None:
        raise TimeoutError("Authorization timed out. Please try again.")
    
    return server.auth_code


def exchange_code_for_tokens(app_key: str, app_secret: str, auth_code: str, redirect_uri: str = "http://localhost:8080/auth") -> dict:
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
    parser = argparse.ArgumentParser(description='Setup Dropbox OAuth 2.0 refresh token')
    parser.add_argument('--app-key', required=True, help='Dropbox app key')
    parser.add_argument('--app-secret', required=True, help='Dropbox app secret')
    
    args = parser.parse_args()
    
    try:
        print("=== Dropbox OAuth 2.0 Setup ===")
        print("This will help you get a refresh token for long-term Dropbox access.")
        print()
        
        # Step 1: Get authorization code
        auth_code = get_authorization_code(args.app_key)
        print(f"✓ Authorization code received")
        
        # Step 2: Exchange for tokens
        print("Exchanging code for tokens...")
        tokens = exchange_code_for_tokens(args.app_key, args.app_secret, auth_code)
        
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
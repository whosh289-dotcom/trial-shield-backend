import re

with open('server.py', 'r') as f:
    content = f.read()

oauth_logic = """
        elif path == "/api/auth/google":
            if not os.path.exists("client_secret.json"):
                # Serve an instruction page
                html = \"\"\"
                <html>
                <body style="font-family:sans-serif; padding:40px; background:#0f172a; color:white; line-height:1.6;">
                    <h2>⚠️ Google OAuth Not Configured Yet</h2>
                    <p>To make "Sign in with Google" actually work, you need to tell Google about your app!</p>
                    <ol>
                        <li>Go to the <a href="https://console.cloud.google.com/" style="color:#38bdf8;">Google Cloud Console</a>.</li>
                        <li>Create a New Project.</li>
                        <li>Go to <b>APIs & Services > Credentials</b>.</li>
                        <li>Click <b>Create Credentials > OAuth client ID</b>.</li>
                        <li>Set Application type to <b>Web application</b>.</li>
                        <li>Add Authorized redirect URI: <code>http://localhost:5055/api/auth/google/callback</code></li>
                        <li>Click Download JSON, rename it to <b>client_secret.json</b>, and place it in this folder.</li>
                        <li>Restart the server.</li>
                    </ol>
                    <p><i>(Or, you can use the legacy App Password method if you prefer not to use OAuth!)</i></p>
                    <button onclick="window.history.back()" style="padding:10px 20px; background:#22c55e; border:none; border-radius:5px; color:white; cursor:pointer;">Go Back</button>
                </body>
                </html>
                \"\"\"
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
                return

            try:
                import google_auth_oauthlib.flow
                flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                    'client_secret.json',
                    scopes=['https://www.googleapis.com/auth/gmail.readonly']
                )
                flow.redirect_uri = 'http://localhost:5055/api/auth/google/callback'
                authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
                self.send_response(302)
                self.send_header("Location", authorization_url)
                self.end_headers()
            except ImportError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Please run: pip3 install google-auth-oauthlib")
            return

        elif path == "/api/auth/google/callback":
            try:
                import google_auth_oauthlib.flow
                flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                    'client_secret.json',
                    scopes=['https://www.googleapis.com/auth/gmail.readonly'],
                    state=urllib.parse.parse_qs(parsed.query).get('state', [''])[0]
                )
                flow.redirect_uri = 'http://localhost:5055/api/auth/google/callback'
                # fetch token
                url = self.path
                flow.fetch_token(authorization_response="http://localhost:5055" + url)
                credentials = flow.credentials
                # Save to database
                set_setting('google_oauth_token', credentials.token)
                set_setting('google_oauth_refresh', credentials.refresh_token)
                
                self.send_response(302)
                self.send_header("Location", "/?google_auth_success=true")
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"OAuth Error: {str(e)}".encode('utf-8'))
            return
"""

# Replace the mock auth logic
pattern = re.compile(r'elif path == "/api/auth/google":.*?return', re.DOTALL)
content = pattern.sub(oauth_logic.strip(), content)

with open('server.py', 'w') as f:
    f.write(content)

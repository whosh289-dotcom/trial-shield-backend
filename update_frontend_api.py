import re

with open('static/index.html', 'r') as f:
    content = f.read()

# Add API_BASE variable
api_base_js = """
    // --- API CONFIGURATION ---
    // When deploying the frontend to Cloudflare Pages, change this to your backend URL (e.g., 'https://your-backend.render.com')
    // Leave it empty ('') when running locally via python server.py
    const API_BASE = ''; 
"""
content = content.replace("let activeTab = 'watch';", api_base_js + "\n    let activeTab = 'watch';")

# Update fetch calls
content = content.replace("fetch('/api/", "fetch(`${API_BASE}/api/")

# Update EventSource
content = content.replace("new EventSource('/api/stream')", "new EventSource(`${API_BASE}/api/stream`)")

# Update OAuth redirect
content = content.replace("window.location.href='/api/auth/google'", "window.location.href = API_BASE + '/api/auth/google'")

with open('static/index.html', 'w') as f:
    f.write(content)

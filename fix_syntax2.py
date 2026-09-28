with open('static/index.html', 'r') as f:
    content = f.read()

content = content.replace("`${API_BASE}/api/trials', {", "`${API_BASE}/api/trials`, {")

with open('static/index.html', 'w') as f:
    f.write(content)

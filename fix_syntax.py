with open('static/index.html', 'r') as f:
    content = f.read()

# Fix mixed quotes
content = content.replace("`${API_BASE}/api/trials')", "`${API_BASE}/api/trials` )")
content = content.replace("`${API_BASE}/api/simulate-email'", "`${API_BASE}/api/simulate-email`")
content = content.replace("`${API_BASE}/api/trials/nag'", "`${API_BASE}/api/trials/nag`")
content = content.replace("`${API_BASE}/api/trials/defuse'", "`${API_BASE}/api/trials/defuse`")
content = content.replace("`${API_BASE}/api/test-notification'", "`${API_BASE}/api/test-notification`")
content = content.replace("`${API_BASE}/api/settings'", "`${API_BASE}/api/settings`")
content = content.replace("`${API_BASE}/api/scan-imap'", "`${API_BASE}/api/scan-imap`")
content = content.replace("`${API_BASE}/api/logs'", "`${API_BASE}/api/logs`")
content = content.replace("`${API_BASE}/api/stream')", "`${API_BASE}/api/stream`)")
content = content.replace("`${API_BASE}/api/audit/transactions'", "`${API_BASE}/api/audit/transactions`")

with open('static/index.html', 'w') as f:
    f.write(content)

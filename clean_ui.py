with open('static/index.html', 'r') as f:
    content = f.read()

# Replace the entire Alert Channels block in settings
new_channels = """
        <!-- Alert Channels -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-bullhorn text-emerald-400"></i> Relentless Nag Channels
          </h2>

          <div class="space-y-4">
            <div class="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800 mt-2">
              <div>
                <div class="text-sm font-semibold text-white">Browser Push Notifications</div>
                <div class="text-xs text-slate-400">Receive native alerts directly via your browser (iOS/Android/Desktop PWA)</div>
              </div>
              <button onclick="requestPushPermissions()" class="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-1.5 px-3 rounded shadow-lg shadow-emerald-900/20">Enable Push</button>
            </div>
          </div>
        </div>
"""

import re
# We need to replace from <!-- Alert Channels --> to <!-- OAUTH & IMAP Connection -->
pattern = re.compile(r'<!-- Alert Channels -->.*?<!-- OAUTH & IMAP Connection -->', re.DOTALL)
content = pattern.sub(new_channels + '\n        <!-- OAUTH & IMAP Connection -->', content)

# Clean up loadSettings
load_js_new = """
    async function loadSettings() {
      try {
        const res = await fetch('/api/settings');
        const { settings } = await res.json();
        document.getElementById('setting-imap-server').value = settings.imap_server || '';
        document.getElementById('setting-imap-port').value = settings.imap_port || '993';
        document.getElementById('setting-imap-user').value = settings.imap_user || '';
        if (settings.has_imap_password) {
          document.getElementById('setting-imap-pass').placeholder = '•••••••• (Stored)';
        }
      } catch (e) {
        console.error(e);
      }
    }
"""
pattern = re.compile(r'async function loadSettings\(\) \{.*?\}(?=\s*async function saveSettings)', re.DOTALL)
content = pattern.sub(load_js_new.strip(), content)

# Clean up saveSettings
save_js_new = """
    async function saveSettings() {
      const payload = {
        imap_server: document.getElementById('setting-imap-server').value.trim(),
        imap_port: document.getElementById('setting-imap-port').value.trim(),
        imap_user: document.getElementById('setting-imap-user').value.trim(),
      };
      const pass = document.getElementById('setting-imap-pass').value.trim();
      if (pass && pass !== '••••••••') {
        payload.imap_password = pass;
      }

      try {
        await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        showToast("Settings saved successfully!");
      } catch (e) {
        alert("Failed to save settings");
      }
    }
"""
pattern = re.compile(r'async function saveSettings\(\) \{.*?\}(?=\s*async function triggerImapScan)', re.DOTALL)
content = pattern.sub(save_js_new.strip(), content)


# Remove "Test Mac Alert" button from header
content = content.replace('<i class="fa-solid fa-bell text-emerald-400"></i> Test Mac Alert', '<i class="fa-solid fa-bell text-emerald-400"></i> Test Push Alert')

with open('static/index.html', 'w') as f:
    f.write(content)

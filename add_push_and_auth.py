with open('static/index.html', 'r') as f:
    content = f.read()

# 1. Update the Settings Tab with "Connect Gmail via OAuth"
oauth_ui = """
        <!-- IMAP / Gmail Connection -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <i class="fa-brands fa-google text-emerald-400"></i> Connect Google Account
          </h2>
          <p class="text-xs text-slate-400">
            Securely link your Gmail using official Google OAuth. We will only request read-access to scan for trial and cancellation emails.
          </p>
          
          <div id="oauth-status-container" class="flex items-center gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800">
             <button onclick="window.location.href='/api/auth/google'" class="px-5 py-2.5 rounded-lg bg-white hover:bg-slate-200 text-slate-900 font-bold text-sm transition flex items-center gap-3">
               <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" class="w-4 h-4" />
               Sign in with Google
             </button>
             <span id="oauth-status-text" class="text-sm font-semibold text-slate-400">Not connected</span>
          </div>
          
          <div class="border-t border-slate-800 pt-4 mt-4">
             <p class="text-xs text-slate-500 mb-2 font-semibold">OR Use Legacy IMAP / App Password</p>
"""
content = content.replace("<!-- IMAP Inbox Connection -->", "<!-- OAUTH & IMAP Connection -->")
content = content.replace("""<div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-inbox text-emerald-400"></i> Automatic Inbox Sync (IMAP)
          </h2>""", oauth_ui)
          
# Close the div we opened for legacy IMAP (actually it's just replacing the header so it wraps correctly)
content = content.replace("Google Account &gt; Security &gt; App Passwords).", "Google Account &gt; Security &gt; App Passwords).\n          </div>")


# 2. Add Push Notification Enable button
push_ui = """
            <div class="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800 mt-2">
              <div>
                <div class="text-sm font-semibold text-white">Browser Push Notifications</div>
                <div class="text-xs text-slate-400">Receive alerts directly via browser (iOS/Android PWA)</div>
              </div>
              <button onclick="requestPushPermissions()" class="text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-1.5 px-3 rounded shadow-lg shadow-emerald-900/20">Enable Push</button>
            </div>
"""
content = content.replace('<input type="checkbox" id="setting-voice" class="w-5 h-5 accent-emerald-500 rounded cursor-pointer" />\n            </div>', '<input type="checkbox" id="setting-voice" class="w-5 h-5 accent-emerald-500 rounded cursor-pointer" />\n            </div>' + push_ui)

# 3. Add JS for Service Worker, SSE, and Notification Permission
js_code = """
    // 1. Service Worker for PWA
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').then(reg => {
          console.log('ServiceWorker registered:', reg.scope);
        }).catch(err => {
          console.log('ServiceWorker registration failed:', err);
        });
      });
    }

    // 2. Request Push Permissions
    function requestPushPermissions() {
      if (!('Notification' in window)) {
        alert("This browser does not support desktop notification");
        return;
      }
      Notification.requestPermission().then(permission => {
        if (permission === "granted") {
          showToast("Push notifications enabled!");
          new Notification("Trial Shield", { body: "Push alerts are active. You're protected!" });
        } else {
          alert("Permission denied for push notifications.");
        }
      });
    }

    // 3. Connect to Server-Sent Events (SSE) for Real-Time Browser Nags
    const evtSource = new EventSource('/api/stream');
    evtSource.onmessage = function(event) {
      const data = JSON.parse(event.data);
      // Trigger Web Push Notification if granted
      if (Notification.permission === "granted") {
        navigator.serviceWorker.ready.then(reg => {
           reg.showNotification(data.title, {
             body: data.body,
             icon: 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🛡️</text></svg>',
             vibrate: [200, 100, 200]
           });
        });
      } else {
        // Fallback toast if push denied but tab is open
        showToast("🚨 " + data.body);
      }
    };

    // 4. Check for mock OAuth success
    window.addEventListener('load', () => {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('google_auth_success')) {
         showToast("Google Account linked successfully!");
         const statusTxt = document.getElementById('oauth-status-text');
         if (statusTxt) {
           statusTxt.innerHTML = '<span class="text-emerald-400"><i class="fa-solid fa-circle-check"></i> Connected as User</span>';
         }
         window.history.replaceState({}, document.title, "/");
         setTimeout(() => switchTab('settings'), 500);
      }
    });

    const MOCK_TRANSACTIONS = [
"""
content = content.replace("const MOCK_TRANSACTIONS = [", js_code)

with open('static/index.html', 'w') as f:
    f.write(content)

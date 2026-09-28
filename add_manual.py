import re

with open('server.py', 'r') as f:
    content = f.read()

# Add the POST /api/trials endpoint logic
post_logic = """
        elif path == "/api/trials":
            service_name = payload.get("service_name")
            trial_end_date = payload.get("trial_end_date")
            cost = payload.get("cost", "")
            cancel_url = payload.get("cancel_url", "")
            
            if not service_name or not trial_end_date:
                self._send_json({"error": "Missing required fields"}, status=400)
                return
                
            if len(trial_end_date) == 10: # YYYY-MM-DD
                trial_end_date += " 23:59:59"
                
            from database import add_trial
            trial_id = add_trial(
                service_name=service_name,
                sender_email="Manual Entry",
                subject="Manually Added",
                trial_end_date=trial_end_date,
                cost=cost,
                cancel_url=cancel_url,
                raw_snippet="Manually added by user."
            )
            self._send_json({"success": True, "trial_id": trial_id})
            return
"""
content = content.replace('elif path == "/api/simulate-email":', post_logic.strip() + '\n\n        elif path == "/api/simulate-email":')

with open('server.py', 'w') as f:
    f.write(content)


with open('static/index.html', 'r') as f:
    html = f.read()

# 1. Add "Add Manual" Button to the Active Watchlist UI
manual_btn = """
      <div class="flex items-center justify-between mb-2">
        <h2 class="text-xl font-bold text-white">Active Watchlist</h2>
        <button onclick="document.getElementById('manual-modal').classList.remove('hidden')" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition flex items-center gap-2 shadow-lg shadow-emerald-950">
          <i class="fa-solid fa-plus"></i> Add Manual Subscription
        </button>
      </div>
      <div id="active-trials-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
"""
html = html.replace('<div id="active-trials-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">', manual_btn)

# 2. Add Modal HTML
modal_html = """
  <!-- MANUAL SUBSCRIPTION MODAL -->
  <div id="manual-modal" class="hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
    <div class="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
      <div class="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <h3 class="text-lg font-bold text-white flex items-center gap-2"><i class="fa-solid fa-pen-to-square text-emerald-400"></i> Manual Subscription</h3>
        <button onclick="document.getElementById('manual-modal').classList.add('hidden')" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-xl"></i></button>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Service / App Name *</label>
          <input type="text" id="man-name" placeholder="e.g. Canva Pro" class="w-full px-4 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-emerald-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Expiration / Renewal Date *</label>
          <input type="date" id="man-date" class="w-full px-4 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-emerald-500 [color-scheme:dark]" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="block text-xs font-semibold text-slate-300 mb-1">Cost / Fee (Optional)</label>
            <input type="text" id="man-cost" placeholder="e.g. $12.99/mo" class="w-full px-4 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-emerald-500" />
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Cancellation Link (Optional)</label>
          <input type="url" id="man-link" placeholder="https://..." class="w-full px-4 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-emerald-500 text-xs" />
        </div>
        <button onclick="submitManualTrial()" class="w-full mt-2 px-4 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm transition shadow-lg shadow-emerald-900/20">
          Save & Start Watchdog
        </button>
      </div>
    </div>
  </div>
"""
html = html.replace('</main>', '</main>\n' + modal_html)

# 3. Add JS Function
js_submit = """
    async function submitManualTrial() {
      const service_name = document.getElementById('man-name').value.trim();
      const trial_end_date = document.getElementById('man-date').value.trim();
      const cost = document.getElementById('man-cost').value.trim();
      const cancel_url = document.getElementById('man-link').value.trim();

      if (!service_name || !trial_end_date) {
        alert("Please provide the service name and expiration date.");
        return;
      }

      try {
        const res = await fetch('/api/trials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service_name, trial_end_date, cost, cancel_url })
        });
        const data = await res.json();
        
        if (data.success) {
          showToast(`🛡️ ${service_name} added to the Watchlist!`);
          document.getElementById('manual-modal').classList.add('hidden');
          
          // Clear inputs
          document.getElementById('man-name').value = '';
          document.getElementById('man-date').value = '';
          document.getElementById('man-cost').value = '';
          document.getElementById('man-link').value = '';
          
          fetchTrials(true);
        } else {
          alert("Error: " + data.error);
        }
      } catch (e) {
        console.error(e);
        alert("Failed to add manual subscription.");
      }
    }
"""
html = html.replace('// Auto-poll trials status every 10 seconds', js_submit + '\n    // Auto-poll trials status every 10 seconds')

with open('static/index.html', 'w') as f:
    f.write(html)

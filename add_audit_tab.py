import re

with open('static/index.html', 'r') as f:
    content = f.read()

# 1. Add tab button
btn_html = """
        <button onclick="switchTab('audit')" id="tab-btn-audit" class="tab-btn px-4 py-2 rounded-lg text-sm font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition flex items-center gap-2">
          <i class="fa-solid fa-magnifying-glass-dollar"></i> Bank Audit
        </button>
"""
content = content.replace("<!-- NAVIGATION TABS -->", "<!-- NAVIGATION TABS -->" + btn_html)

# 2. Add tab content
tab_html = """
    <!-- TAB: BANK AUDIT -->
    <div id="tab-audit" class="tab-content hidden flex flex-col gap-6">
      <div class="bg-indigo-950/20 border border-indigo-800/40 rounded-2xl p-6">
        <h2 class="text-lg font-bold text-white mb-2 flex items-center gap-2">
          <i class="fa-solid fa-building-columns text-indigo-400"></i> Smart Bank Transaction Auditor
        </h2>
        <p class="text-sm text-slate-300 mb-6">
          Upload a CSV or JSON of your bank transactions. We'll automatically identify forgotten recurring subscriptions and ask you: <strong>"Do you really use it?"</strong>
        </p>

        <div class="mb-6 flex gap-3">
            <button onclick="simulateBankAudit()" class="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition shadow-lg shadow-indigo-950 flex items-center gap-2">
              <i class="fa-solid fa-magic"></i> Scan Mock Transactions
            </button>
            <span id="audit-status" class="text-xs text-slate-400 self-center"></span>
        </div>

        <div id="audit-results" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <!-- Rendered dynamically -->
        </div>
      </div>
    </div>
"""
content = content.replace("<!-- TAB 5: NAG LOGS -->", tab_html + "\n    <!-- TAB 5: NAG LOGS -->")

# 3. Add JS
js_html = """
    const MOCK_TRANSACTIONS = [
      { date: "2026-08-01", description: "AMZN PRIME VIDEO WEB", amount: 14.99 },
      { date: "2026-09-01", description: "AMZN PRIME VIDEO WEB", amount: 14.99 },
      { date: "2026-07-15", description: "UBER EATS", amount: 25.50 },
      { date: "2026-08-10", description: "PLANET FITNESS", amount: 10.00 },
      { date: "2026-09-10", description: "PLANET FITNESS", amount: 10.00 },
      { date: "2026-07-20", description: "DOORDASH", amount: 32.10 },
      { date: "2026-08-25", description: "CHATGPT SUBSCRIPTION", amount: 20.00 },
      { date: "2026-09-25", description: "CHATGPT SUBSCRIPTION", amount: 20.00 },
    ];

    async function simulateBankAudit() {
      const statusEl = document.getElementById('audit-status');
      statusEl.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-indigo-400"></i> Analyzing 893 transactions...`;
      
      try {
        const res = await fetch('/api/audit/transactions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transactions: MOCK_TRANSACTIONS })
        });
        const data = await res.json();
        renderAuditResults(data.detected || []);
        statusEl.innerHTML = `<span class="text-emerald-400">Scan complete! Found ${data.detected?.length || 0} recurring charges.</span>`;
      } catch (e) {
        statusEl.innerHTML = `<span class="text-red-400">Scan failed</span>`;
      }
    }

    function renderAuditResults(items) {
      const container = document.getElementById('audit-results');
      container.innerHTML = '';
      
      if (items.length === 0) {
        container.innerHTML = `<div class="col-span-full p-8 text-center text-slate-400">No recurring charges found.</div>`;
        return;
      }
      
      items.forEach((item, idx) => {
        const card = document.createElement('div');
        card.id = `audit-card-${idx}`;
        card.className = "rounded-2xl border border-indigo-900/50 bg-slate-900/80 p-5 flex flex-col justify-between";
        card.innerHTML = `
          <div>
            <div class="flex justify-between items-start mb-3">
              <h3 class="font-bold text-white">${item.service_name}</h3>
              <span class="text-xs bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded uppercase font-bold">${item.interval}</span>
            </div>
            <div class="text-2xl font-bold text-red-400 mb-1">$${item.cost}</div>
            <div class="text-xs text-slate-400 mb-4">Last charged: ${item.last_charge_date}</div>
            
            <div class="bg-indigo-950/40 p-4 rounded-xl border border-indigo-900/50 text-center">
              <p class="font-semibold text-slate-200 mb-3">🤔 Do you really use this?</p>
              <div class="flex gap-2">
                <button onclick="confirmUsage(${idx}, '${item.service_name}', true)" class="flex-1 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold py-2 rounded transition">Yes, keep it</button>
                <button onclick="confirmUsage(${idx}, '${item.service_name}', false)" class="flex-1 bg-red-600 hover:bg-red-500 text-white text-xs font-bold py-2 rounded transition shadow-lg shadow-red-900/20">No, cancel it!</button>
              </div>
            </div>
          </div>
        `;
        container.appendChild(card);
      });
    }

    function confirmUsage(idx, service, keep) {
      const card = document.getElementById(`audit-card-${idx}`);
      if (keep) {
        card.innerHTML = `<div class="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400"><i class="fa-solid fa-check-circle text-3xl mb-2 text-emerald-500"></i><p>Kept ${service}</p></div>`;
      } else {
        card.innerHTML = `<div class="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400"><i class="fa-solid fa-bullseye text-3xl mb-2 text-red-500"></i><p class="text-sm text-white font-bold mb-1">Target Acquired</p><p class="text-xs">Added to Nag Watchlist!</p></div>`;
        // In a real app, this would POST to /api/trials to add it to the watchdog queue!
      }
    }
"""
content = content.replace("// Initial load", js_html + "\n    // Initial load")

with open('static/index.html', 'w') as f:
    f.write(content)

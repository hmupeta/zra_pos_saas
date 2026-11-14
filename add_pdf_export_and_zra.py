import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add ZRA VAT Return Tab and PDF Print logic to reports.html
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "reports.html"
h_content = html_path.read_text(encoding="utf-8")

# A. Add the ZRA tab to the tabs array
h_content = h_content.replace(
    "{ id: 'category', label: 'Sales by Category' },",
    "{ id: 'category', label: 'Sales by Category' },\n      { id: 'zra', label: 'ZRA VAT Return' },"
)

# B. Add the ZRA HTML block before the closing content div
zra_html = '''
      <!-- ZRA VAT Return -->
      <div x-show="tab === 'zra'" class="card p-6 max-w-2xl border-t-4 border-brand-600">
        <div class="flex justify-between items-start mb-6">
          <div>
            <h2 class="text-xl font-bold text-slate-800">ZRA VAT Return Summary</h2>
            <p class="text-sm text-gray-500">For the period: <span x-text="startDate"></span> to <span x-text="endDate"></span></p>
          </div>
          <button @click="printReport()" class="btn-secondary flex items-center gap-2 text-sm">
            <i data-lucide="printer" class="w-4 h-4"></i> Print / PDF
          </button>
        </div>
        
        <div class="grid grid-cols-2 gap-6 border-b pb-6 mb-6">
          <div class="bg-gray-50 p-4 rounded-lg border">
            <div class="text-sm text-gray-500 font-medium">Gross Sales (VAT Inclusive)</div>
            <div class="text-3xl font-bold text-slate-800 mt-1" x-text="formatCurrency(data?.gross_sales)"></div>
          </div>
          <div class="bg-brand-50 p-4 rounded-lg border border-brand-100">
            <div class="text-sm text-brand-700 font-medium">Output VAT Collected</div>
            <div class="text-3xl font-bold text-brand-700 mt-1" x-text="formatCurrency(data?.output_vat)"></div>
          </div>
          <div>
            <div class="text-sm text-gray-500 font-medium">Net Sales (Excluding VAT)</div>
            <div class="text-xl font-semibold text-slate-700" x-text="formatCurrency(data?.net_sales)"></div>
          </div>
          <div>
            <div class="text-sm text-gray-500 font-medium">Total Transactions</div>
            <div class="text-xl font-semibold text-slate-700" x-text="data?.transaction_count"></div>
          </div>
        </div>
        <div class="bg-blue-50 text-blue-800 text-sm p-4 rounded-lg flex gap-3">
          <i data-lucide="info" class="w-5 h-5 flex-shrink-0"></i>
          <p>This shows Output VAT only. To calculate your final ZRA liability, you must subtract your Input VAT (from Supplier Purchases).</p>
        </div>
      </div>
'''
h_content = h_content.replace("    </div>\n  </div>\n</div>\n\n<script>", zra_html + "\n    </div>\n  </div>\n</div>\n\n<script>")

# C. Add the printReport() JS function
print_js = '''
    async printReport() {
      if (!this.data) { alert('No data to print'); return; }
      
      // Fetch company details for the header
      let company = { name: 'Nimbus POS', address: '', phone: '', logo_url: null };
      try {
        const c = await apiFetch('/auth/company/');
        company = c;
      } catch(e) { console.error("Could not load company details", e); }

      let tableHtml = '';
      
      if (this.tab === 'trial') {
        tableHtml = `
          <h2>Trial Balance</h2>
          <table><thead><tr><th>Code</th><th>Account</th><th class="right">Debit</th><th class="right">Credit</th></tr></thead>
          <tbody>
            ${this.data.accounts.map(a => `<tr><td>${a.code}</td><td>${a.name}</td><td class="right">${a.debit > 0 ? formatCurrency(a.debit) : '-'}</td><td class="right">${a.credit > 0 ? formatCurrency(a.credit) : '-'}</td></tr>`).join('')}
            <tr class="total-row"><td colspan="2">TOTALS</td><td class="right">${formatCurrency(this.data.total_debit)}</td><td class="right">${formatCurrency(this.data.total_credit)}</td></tr>
          </tbody></table>
        `;
      } else if (this.tab === 'balance') {
        tableHtml = `
          <h2>Balance Sheet</h2>
          <div class="section">
            <h3>Assets: ${formatCurrency(this.data.assets)}</h3>
            <h3>Liabilities: ${formatCurrency(this.data.liabilities)}</h3>
            <h3>Equity: ${formatCurrency(this.data.equity)}</h3>
            <h3>Net Income: ${formatCurrency(this.data.net_income)}</h3>
          </div>
        `;
      } else if (this.tab === 'income') {
        tableHtml = `
          <h2>Income Statement</h2>
          <div class="section">
            <p><strong>Revenue:</strong> ${formatCurrency(this.data.revenue)}</p>
            <p><strong>Expenses:</strong> ${formatCurrency(this.data.expenses)}</p>
            <h3 class="total-row">Net Income: ${formatCurrency(this.data.net_income)}</h3>
          </div>
        `;
      } else if (this.tab === 'cash_flow') {
        tableHtml = `
          <h2>Cash Flow Statement</h2>
          <div class="section">
            <p><strong>Inflows:</strong> ${formatCurrency(this.data.inflows)}</p>
            <p><strong>Outflows:</strong> ${formatCurrency(this.data.outflows)}</p>
            <h3 class="total-row">Net Cash Flow: ${formatCurrency(this.data.net_cash_flow)}</h3>
          </div>
        `;
      } else if (this.tab === 'category') {
        tableHtml = `
          <h2>Sales by Category</h2>
          <table><thead><tr><th>Category</th><th class="right">Qty</th><th class="right">Revenue</th></tr></thead>
          <tbody>
            ${this.data.map(c => `<tr><td>${c.category}</td><td class="right">${c.qty}</td><td class="right">${formatCurrency(c.revenue)}</td></tr>`).join('')}
          </tbody></table>
        `;
      } else if (this.tab === 'zra') {
        tableHtml = `
          <h2>ZRA VAT Return Summary</h2>
          <div class="section">
            <p><strong>Gross Sales (VAT Inclusive):</strong> ${formatCurrency(this.data.gross_sales)}</p>
            <p><strong>Output VAT Collected:</strong> ${formatCurrency(this.data.output_vat)}</p>
            <p><strong>Net Sales (Excluding VAT):</strong> ${formatCurrency(this.data.net_sales)}</p>
            <p><strong>Total Transactions:</strong> ${this.data.transaction_count}</p>
          </div>
        `;
      }

      const printWindow = window.open('', '_blank');
      printWindow.document.write(`
        <html>
          <head>
            <title>Financial Report - ${company.name}</title>
            <style>
              body { font-family: 'Arial', sans-serif; padding: 40px; color: #333; }
              .header { text-align: center; border-bottom: 2px solid #4f46e5; padding-bottom: 20px; margin-bottom: 30px; }
              .logo { max-height: 80px; margin-bottom: 10px; }
              .company-name { font-size: 24px; font-weight: bold; color: #4f46e5; margin: 0; }
              .company-details { font-size: 14px; color: #666; margin-top: 5px; }
              h2 { font-size: 20px; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px; }
              table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
              th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
              th { background-color: #f9fafb; font-weight: bold; }
              .right { text-align: right; }
              .total-row { font-weight: bold; font-size: 16px; border-top: 2px solid #333; }
              .section p { margin: 10px 0; font-size: 16px; }
              .footer { text-align: center; font-size: 12px; color: #999; margin-top: 50px; border-top: 1px solid #eee; padding-top: 10px; }
            </style>
          </head>
          <body>
            <div class="header">
              ${company.logo_url ? `<img src="${window.location.origin}${company.logo_url}" class="logo">` : ''}
              <h1 class="company-name">${company.name}</h1>
              <div class="company-details">${company.address || ''}</div>
              <div class="company-details">TPIN: ${company.tpin || ''} | Phone: ${company.phone || ''}</div>
            </div>
            
            <div style="text-align: right; font-size: 14px; margin-bottom: 20px;">
              <strong>Period:</strong> ${this.startDate} to ${this.endDate}<br>
              <strong>Generated:</strong> ${new Date().toLocaleString()}
            </div>

            ${tableHtml}

            <div class="footer">
              Generated by Nimbus POS
            </div>
            <script>
              window.onload = () => { window.print(); setTimeout(() => window.close(), 100); };
            <\/script>
          </body>
        </html>
      `);
      printWindow.document.close();
    },
'''
h_content = h_content.replace("    exportCsv(filename, rows) {", print_js + "\n    exportCsv(filename, rows) {")

# D. Add the fetch logic for the ZRA tab
h_content = h_content.replace(
    "if (this.tab === 'category') endpoint = '/reports/sales-by-category/';",
    "if (this.tab === 'category') endpoint = '/reports/sales-by-category/';\n      if (this.tab === 'zra') endpoint = '/reports/zra-tax/';"
)

# E. Add a "Print / PDF" button to all other tabs via the header
h_content = h_content.replace(
    '<button @click="loadCustom()" class="btn-primary text-sm py-1.5 px-4 ml-2">Generate</button>',
    '''<button @click="loadCustom()" class="btn-primary text-sm py-1.5 px-4 ml-2">Generate</button>
        <button @click="printReport()" class="btn-secondary text-sm py-1.5 px-4 flex items-center gap-1" :disabled="!data">
          <i data-lucide="printer" class="w-4 h-4"></i> PDF
        </button>'''
)

html_path.write_text(h_content, encoding="utf-8")
print("✅ Added ZRA Tax Tab and PDF Export functionality to reports.html.")

# ============================================================
# 2. Add ZRA link to the Sidebar Nav
# ============================================================
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
n_content = nav_path.read_text(encoding="utf-8")

if "/reports?tab=zra" not in n_content:
    # Add it right below Financial Reports
    n_content = n_content.replace(
        '<a href="/reports" class="nav-link"',
        '<a href="/reports" class="nav-link"'
    )
    # Actually, let's just make it point to the ZRA tab by default if clicked
    # But to keep it simple, let's just create a dedicated menu item that opens the reports page.
    # We can't easily deep link with Alpine tabs without JS, so let's add a query param.
    
    # Better: Add a dedicated "ZRA Tax Return" menu item that points to the report page.
    if 'href="/reports/zra"' not in n_content:
         n_content = n_content.replace(
            '<a href="/reports" class="nav-link"',
            '<a href="/reports" class="nav-link"'
        )

# Let's add a dedicated ZRA link to the sidebar
if "ZRA Tax Return" not in n_content:
    # Insert after Financial Reports
    n_content = n_content.replace(
        '<i data-lucide="bar-chart-2" class="w-4 h-4 mr-3"></i> Financial Reports</a>',
        '''<i data-lucide="bar-chart-2" class="w-4 h-4 mr-3"></i> Financial Reports</a>
    <a href="/reports" onclick="localStorage.setItem('open_zra', 'true')" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
      <i data-lucide="shield-check" class="w-4 h-4 mr-3"></i> ZRA Tax Return</a>'''
    )
    nav_path.write_text(n_content, encoding="utf-8")
    print("✅ Added ZRA Tax Return link to Sidebar.")

# ============================================================
# 3. Handle the sidebar click to open ZRA tab automatically
# ============================================================
# Add a small script to reports.html to check localStorage on load
h_content = html_path.read_text(encoding="utf-8")
if "localStorage.getItem('open_zra')" not in h_content:
    h_content = h_content.replace(
        "x-init=\"load('trial')\"",
        "x-init=\"if(localStorage.getItem('open_zra')) { localStorage.removeItem('open_zra'); load('zra'); } else { load('trial'); }\""
    )
    html_path.write_text(h_content, encoding="utf-8")
    print("✅ Added auto-open logic for ZRA tab.")

print("\n🎉 Done! Restart the server and check the Financial Reports page.")
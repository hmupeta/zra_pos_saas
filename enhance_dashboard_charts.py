import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Backend (reports/views.py) to aggregate chart data
# ============================================================
reports_views_path = BACKEND_PATH / "reports" / "views.py"
new_views = '''
from datetime import timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from sales.models import Invoice, InvoiceItem
from inventory.models import Product
from core.isolation import branch_filter

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales_summary(request):
    period = request.query_params.get("period", "today")
    now = timezone.now()
    start = now.replace(hour=0, minute=0, second=0) if period == "today" else now - timedelta(days=7)
    qs = branch_filter(request, Invoice.objects.filter(created_at__gte=start, status="PAID"))
    agg = qs.aggregate(total=Sum("total"), count=Count("id"), tax=Sum("tax_total"))
    return Response({
        "period": period,
        "total_sales": float(agg["total"] or 0),
        "transaction_count": agg["count"] or 0,
        "total_tax": float(agg["tax"] or 0),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_7_days = today - timedelta(days=6)
    
    # Base Querysets
    branch_invoices = branch_filter(request, Invoice.objects.all())
    today_invoices = branch_invoices.filter(created_at__gte=today, status="PAID")
    
    # 1. KPIs
    agg = today_invoices.aggregate(t=Sum("total"), c=Count("id"))
    total_products = Product.objects.filter(tenant=request.tenant, company=request.branch, is_active=True).count()
    low_stock = Product.objects.filter(tenant=request.tenant, company=request.branch, current_stock__lte=10, is_active=True).count()

    # 2. Sales Trend (Last 7 Days)
    trend_qs = branch_invoices.filter(created_at__gte=last_7_days, status="PAID") \\
        .annotate(date=TruncDate('created_at')) \\
        .values('date') \\
        .annotate(total=Sum('total')) \\
        .order_by('date')
    
    trend_labels = [item['date'].strftime('%a, %d %b') for item in trend_qs]
    trend_data = [float(item['total']) for item in trend_qs]

    # 3. Payment Methods
    pm_qs = branch_invoices.filter(status="PAID").values('payment_method').annotate(total=Sum('total'))
    pm_labels = [item['payment_method'] for item in pm_qs]
    pm_data = [float(item['total']) for item in pm_qs]

    # 4. Top Selling Products
    top_qs = InvoiceItem.objects.filter(invoice__in=branch_invoices.filter(status="PAID")) \\
        .values('product__name') \\
        .annotate(qty=Sum('quantity')) \\
        .order_by('-qty')[:5]
    
    top_labels = [item['product__name'] for item in top_qs]
    top_data = [float(item['qty']) for item in top_qs]

    return Response({
        "kpis": {
            "today_sales": float(agg["t"] or 0),
            "today_transactions": agg["c"] or 0,
            "total_products": total_products,
            "low_stock": low_stock,
        },
        "charts": {
            "trend": {"labels": trend_labels, "data": trend_data},
            "payments": {"labels": pm_labels, "data": pm_data},
            "top_products": {"labels": top_labels, "data": top_data}
        },
        "tenant": request.tenant.name if request.tenant else None,
        "branch": request.branch.name if request.branch else None,
    })
'''
reports_views_path.write_text(new_views.strip(), encoding="utf-8")
print("✅ Updated reports/views.py to aggregate chart data")

# ============================================================
# 2. Update Frontend (templates/pos/dashboard.html)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "dashboard.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Dashboard{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="dashboard()" x-init="load()">
    
    <div class="flex justify-between items-end mb-6">
      <div>
        <h1 class="text-2xl font-bold">Dashboard</h1>
        <p class="text-gray-500" x-text="branch + ' · ' + tenant"></p>
      </div>
      <div class="text-sm text-gray-500" x-text="'Last updated: ' + new Date().toLocaleTimeString()"></div>
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="card p-5">
        <div class="text-sm text-gray-500">Today's Sales</div>
        <div class="text-3xl font-bold text-brand-700 mt-1" x-text="formatCurrency(kpis.today_sales)"></div>
      </div>
      <div class="card p-5">
        <div class="text-sm text-gray-500">Transactions</div>
        <div class="text-3xl font-bold mt-1" x-text="kpis.today_transactions"></div>
      </div>
      <div class="card p-5">
        <div class="text-sm text-gray-500">Total Products</div>
        <div class="text-3xl font-bold mt-1" x-text="kpis.total_products"></div>
      </div>
      <div class="card p-5">
        <div class="text-sm text-gray-500">Low Stock Items</div>
        <div class="text-3xl font-bold mt-1" :class="kpis.low_stock > 0 ? 'text-red-600' : 'text-green-600'" x-text="kpis.low_stock"></div>
      </div>
    </div>

    <!-- Charts Row 1 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      
      <!-- Sales Trend (Spans 2 columns) -->
      <div class="card p-6 lg:col-span-2">
        <h2 class="font-semibold mb-4 text-gray-700">Sales Trend (Last 7 Days)</h2>
        <div class="relative h-72 w-full">
          <canvas id="trendChart"></canvas>
        </div>
      </div>

      <!-- Payment Methods -->
      <div class="card p-6">
        <h2 class="font-semibold mb-4 text-gray-700">Payment Methods</h2>
        <div class="relative h-72 w-full flex justify-center">
          <canvas id="paymentChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- Top Products -->
      <div class="card p-6">
        <h2 class="font-semibold mb-4 text-gray-700">Top Selling Products</h2>
        <div class="relative h-64 w-full">
          <canvas id="topProductsChart"></canvas>
        </div>
      </div>

      <!-- Quick Info -->
      <div class="card p-6 bg-gradient-to-br from-brand-50 to-white border-brand-100">
        <h2 class="font-semibold mb-2 text-brand-700">Quick Tip</h2>
        <p class="text-sm text-gray-600">
          Use the <strong>Products</strong> tab to receive new stock when a delivery arrives. 
          Keeping inventory up to date ensures the POS never sells items you don't have.
        </p>
        <a href="/products" class="inline-block mt-4 btn-primary text-sm">Go to Inventory</a>
      </div>
    </div>

  </div>
</div>

<!-- Chart.js CDN -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
function dashboard() {
  return {
    branch: '', tenant: '', kpis: {},
    chartsInitialized: false,

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        const d = await apiFetch('/reports/dashboard/');
        this.branch = d.branch || '';
        this.tenant = d.tenant || '';
        this.kpis = d.kpis;

        // Wait for Alpine to render the canvas elements, then draw charts
        this.$nextTick(() => {
          this.renderCharts(d.charts);
        });
      } catch (e) { alert(e.message); }
    },

    renderCharts(data) {
      // Colors
      const brandColor = '#4f46e5';
      const brandLight = 'rgba(79, 70, 229, 0.1)';
      const palette = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

      // 1. Trend Chart (Line)
      const trendCtx = document.getElementById('trendChart').getContext('2d');
      new Chart(trendCtx, {
        type: 'line',
        data: {
          labels: data.trend.labels,
          datasets: [{
            label: 'Sales (K)',
            data: data.trend.data,
            borderColor: brandColor,
            backgroundColor: brandLight,
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: brandColor,
            pointRadius: 4,
            pointHoverRadius: 6
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { borderDash: [4, 4] } },
            x: { grid: { display: false } }
          }
        }
      });

      // 2. Payment Methods (Doughnut)
      const payCtx = document.getElementById('paymentChart').getContext('2d');
      new Chart(payCtx, {
        type: 'doughnut',
        data: {
          labels: data.payments.labels.length ? data.payments.labels : ['No Data'],
          datasets: [{
            data: data.payments.data.length ? data.payments.data : [1],
            backgroundColor: data.payments.data.length ? palette : ['#e5e7eb'],
            borderWidth: 0,
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          cutout: '70%',
          plugins: {
            legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } }
          }
        }
      });

      // 3. Top Products (Bar)
      const prodCtx = document.getElementById('topProductsChart').getContext('2d');
      new Chart(prodCtx, {
        type: 'bar',
        data: {
          labels: data.top_products.labels.length ? data.top_products.labels : ['No Sales'],
          datasets: [{
            label: 'Units Sold',
            data: data.top_products.data.length ? data.top_products.data : [0],
            backgroundColor: brandColor,
            borderRadius: 4,
            barThickness: 24
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { borderDash: [4, 4] } },
            x: { grid: { display: false } }
          }
        }
      });
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Rebuilt dashboard.html with Chart.js visualizations")
print("\n🎉 Done! Restart the server and refresh the Dashboard.")
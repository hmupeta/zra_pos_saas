import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add the Notification Model to Core
# ============================================================
models_path = BACKEND_PATH / "core" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "class SystemNotification" not in m_content:
    m_content += '''

class SystemNotification(models.Model):
    TYPES = [
        ("INFO", "Information"),
        ("WARNING", "Warning"),
        ("ERROR", "Critical Error"),
        ("SUCCESS", "Success"),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPES, default="INFO")
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True, help_text="Where to redirect when clicked")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.tenant.name}"
'''
    models_path.write_text(m_content, encoding="utf-8")
    print("✅ Added SystemNotification model.")

# ============================================================
# 2. Add Signals to trigger notifications
# ============================================================
signals_path = BACKEND_PATH / "core" / "signals.py"
if not signals_path.exists():
    signals_path.write_text("", encoding="utf-8")

s_content = signals_path.read_text(encoding="utf-8")

new_signals = '''
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import SystemNotification

@receiver(post_save, sender="inventory.Product")
def check_low_stock(sender, instance, **kwargs):
    """Trigger an alert when stock falls below reorder level."""
    if instance.current_stock <= instance.reorder_level and instance.is_active:
        today = timezone.now().date()
        # Check if we already alerted about this today to prevent spam
        exists = SystemNotification.objects.filter(
            tenant=instance.tenant,
            title="Low Stock Alert",
            message__contains=instance.name,
            created_at__date=today
        ).exists()
        
        if not exists:
            SystemNotification.objects.create(
                tenant=instance.tenant,
                title="Low Stock Alert",
                message=f"{instance.name} is running low. Only {instance.current_stock} left (Reorder level: {instance.reorder_level}).",
                notification_type="WARNING",
                link="/products"
            )

@receiver(post_save, sender="zra_integration.ZRASubmission")
def check_zra_failure(sender, instance, created, **kwargs):
    """Trigger an alert if a ZRA submission fails."""
    if instance.status == "FAILED":
        SystemNotification.objects.create(
            tenant=instance.invoice.tenant,
            title="ZRA Submission Failed",
            message=f"Invoice {instance.invoice.invoice_number} failed to submit to ZRA. Please retry.",
            notification_type="ERROR",
            link="/zra-compliance"
        )
'''
if "check_low_stock" not in s_content:
    signals_path.write_text(s_content + "\n\n" + new_signals, encoding="utf-8")
    print("✅ Added notification signals.")

# Update core/apps.py to load signals
apps_path = BACKEND_PATH / "core" / "apps.py"
a_content = apps_path.read_text(encoding="utf-8")
if "from . import signals" not in a_content:
    a_content = a_content.replace(
        "def ready(self):",
        "def ready(self):\n        from . import signals  # noqa"
    )
    apps_path.write_text(a_content, encoding="utf-8")
    print("✅ Registered signals in core/apps.py")

# ============================================================
# 3. Add API to fetch and mark notifications as read
# ============================================================
views_path = BACKEND_PATH / "core" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

notif_views = '''
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    qs = SystemNotification.objects.filter(tenant=request.tenant).order_by("-created_at")[:20]
    unread_count = SystemNotification.objects.filter(tenant=request.tenant, is_read=False).count()
    
    return Response({
        "unread_count": unread_count,
        "notifications": [{
            "id": n.id, "title": n.title, "message": n.message,
            "type": n.notification_type, "is_read": n.is_read,
            "link": n.link, "time": n.created_at.strftime("%Y-%m-%d %H:%M")
        } for n in qs]
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notifications_read(request):
    ids = request.data.get("ids", [])
    if ids:
        SystemNotification.objects.filter(tenant=request.tenant, id__in=ids).update(is_read=True)
    else:
        SystemNotification.objects.filter(tenant=request.tenant).update(is_read=True)
    return Response({"success": True})
'''

if "def get_notifications" not in v_content:
    v_content += "\n\n" + notif_views
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Added Notification API views.")

# Update URLs
urls_path = BACKEND_PATH / "core" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "get_notifications" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("notifications/", views.get_notifications, name="get_notifications"),\n    path("notifications/read/", views.mark_notifications_read, name="mark_notifications_read"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
    print("✅ Added Notification URLs.")

# ============================================================
# 4. Add the Bell Icon to the UI (base.html)
# ============================================================
base_path = BACKEND_PATH / "templates" / "pos" / "base.html"
b_content = base_path.read_text(encoding="utf-8")

# The floating notification bell HTML
bell_html = '''
  <!-- Floating Notification Bell -->
  <div class="fixed top-4 right-6 z-[9000]" x-data="notificationApp()" x-init="init()">
    <div class="relative">
      <button @click="toggleDropdown()" class="bg-white p-2.5 rounded-full shadow-lg border border-gray-200 hover:bg-gray-50 transition relative">
        <i data-lucide="bell" class="w-5 h-5 text-slate-600"></i>
        <span x-show="unreadCount > 0" 
              class="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full border-2 border-white"
              x-text="unreadCount"></span>
      </button>

      <!-- Dropdown -->
      <div x-show="open" x-cloak @click.away="open = false" 
           class="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-2xl border border-gray-100 overflow-hidden">
        <div class="p-3 bg-gray-50 border-b flex justify-between items-center">
          <span class="font-bold text-sm text-slate-700">Notifications</span>
          <button @click="markAllRead()" class="text-xs text-brand-600 hover:underline">Mark all read</button>
        </div>
        
        <div class="max-h-96 overflow-y-auto">
          <template x-for="n in notifications" :key="n.id">
            <a :href="n.link || '#'" @click.prevent="handleClick(n)" 
               class="block p-4 border-b hover:bg-gray-50 transition"
               :class="!n.is_read ? 'bg-blue-50/50' : ''">
              <div class="flex items-start gap-3">
                <div class="mt-1">
                  <i data-lucide="alert-circle" class="w-4 h-4" :class="{
                    'text-red-500': n.type === 'ERROR',
                    'text-yellow-500': n.type === 'WARNING',
                    'text-green-500': n.type === 'SUCCESS',
                    'text-blue-500': n.type === 'INFO'
                  }"></i>
                </div>
                <div class="flex-1">
                  <div class="flex justify-between items-start">
                    <span class="font-bold text-sm text-slate-800" x-text="n.title"></span>
                    <span class="text-[10px] text-gray-400" x-text="n.time"></span>
                  </div>
                  <p class="text-xs text-gray-600 mt-1" x-text="n.message"></p>
                </div>
              </div>
            </a>
          </template>
          <div x-show="notifications.length === 0" class="p-6 text-center text-gray-400 text-sm">
            No notifications
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    function notificationApp() {
      return {
        open: false,
        unreadCount: 0,
        notifications: [],
        
        init() {
          if (!localStorage.getItem('token')) return;
          this.fetchNotifications();
          // Poll every 60 seconds
          setInterval(() => this.fetchNotifications(), 60000);
        },

        async fetchNotifications() {
          try {
            const res = await apiFetch('/auth/notifications/');
            this.unreadCount = res.unread_count;
            this.notifications = res.notifications;
            // Re-render icons
            setTimeout(() => { if(window.lucide) lucide.createIcons(); }, 50);
          } catch(e) { /* Ignore polling errors */ }
        },

        toggleDropdown() {
          this.open = !this.open;
          if (this.open) this.fetchNotifications();
        },

        async handleClick(n) {
          if (!n.is_read) {
            await apiFetch('/auth/notifications/read/', { method: 'POST', body: JSON.stringify({ ids: [n.id] }) });
            this.fetchNotifications();
          }
          if (n.link) window.location.href = n.link;
        },

        async markAllRead() {
          await apiFetch('/auth/notifications/read/', { method: 'POST', body: JSON.stringify({}) });
          this.fetchNotifications();
        }
      }
    }
  </script>
'''

if "function notificationApp()" not in b_content:
    b_content = b_content.replace("  <script>\n    // Initialize Lucide icons on page load", bell_html + "\n  <script>\n    // Initialize Lucide icons on page load")
    base_path.write_text(b_content, encoding="utf-8")
    print("✅ Added Notification Bell to base.html.")

# ============================================================
# 5. Run Migrations
# ============================================================
print("\nRunning migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "core"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")
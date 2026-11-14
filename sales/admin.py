from django.contrib import admin
from .models import Shift, Invoice, InvoiceItem


class ItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "tenant", "company", "total", "status", "created_at")
    list_filter = ("status", "tenant", "company")
    inlines = [ItemInline]


admin.site.register(Shift)

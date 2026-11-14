from django.contrib import admin
from .models import Account, Journal, JournalLine


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "tenant", "is_active")
    list_filter = ("account_type", "tenant")


class LineInline(admin.TabularInline):
    model = JournalLine
    extra = 2


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ("journal_number", "date", "tenant", "status", "total_debit", "total_credit")
    inlines = [LineInline]

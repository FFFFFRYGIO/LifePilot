from django.contrib import admin

from .models import Connection


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin[Connection]):
    list_display = ("provider", "account_email", "status", "expires_at", "updated_at")
    # Tokens are deliberately not exposed in the admin.
    fields = ("provider", "account_email", "status", "expires_at", "scopes", "last_error")
    readonly_fields = fields

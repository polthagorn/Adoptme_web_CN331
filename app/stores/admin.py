from django.contrib import admin
from .models import Store, Product

class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'created_at')
    list_filter = ('status', 'store_type')
    search_fields = ('name', 'owner__username')
    actions = ['approve_stores', 'reject_stores']

    def approve_stores(self, request, queryset):
        queryset.update(status='APPROVED')
    approve_stores.short_description = "approve selected stores"

    def reject_stores(self, request, queryset):
        queryset.update(status='REJECTED')
    reject_stores.short_description = "reject selected stores"

admin.site.register(Store, StoreAdmin)
admin.site.register(Product)
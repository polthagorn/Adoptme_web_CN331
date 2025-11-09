from django.contrib import admin
from django.utils.html import format_html
from .models import ShelterProfile

@admin.register(ShelterProfile)
class ShelterProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'user__username')
    readonly_fields = ('profile_image_display', 'cover_image_display', 'document_link')
    actions = ['approve_shelters', 'reject_shelters']

    fieldsets = (
        ('ข้อมูลทั่วไป', {'fields': ('user', 'name', 'description', 'address', 'phone_number', 'status')}),
        ('รูปภาพ', {'fields': ('profile_image', 'profile_image_display', 'cover_image', 'cover_image_display')}),
        ('เอกสารยืนยัน', {'fields': ('verification_document', 'document_link')}),
    )

    def profile_image_display(self, obj):
        if obj.profile_image:
            return format_html('<img src="{}" width="150" />', obj.profile_image.url)
    profile_image_display.short_description = 'ตัวอย่างโปรไฟล์'

    def cover_image_display(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" width="250" />', obj.cover_image.url)
    cover_image_display.short_description = 'ตัวอย่าง Cover'

    def document_link(self, obj):
        if obj.verification_document:
            return format_html('<a href="{}" target="_blank">ดูเอกสาร</a>', obj.verification_document.url)
    document_link.short_description = 'ลิงก์เอกสาร'

    def approve_shelters(self, request, queryset):
        queryset.update(status='APPROVED')
    approve_shelters.short_description = 'อนุมัติสถานะ Shelter ที่เลือก'

    def reject_shelters(self, request, queryset):
        queryset.update(status='REJECTED')
    reject_shelters.short_description = 'ปฏิเสธสถานะ Shelter ที่เลือก'
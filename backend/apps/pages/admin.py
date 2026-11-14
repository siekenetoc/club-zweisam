from django import forms
from django.contrib import admin
from django.utils.html import format_html

from apps.core.permissions import is_platform_admin
from apps.pages.models import PageMedia, StaticPage


class TinyMCETextarea(forms.Textarea):
    def __init__(self, attrs=None):
        default_attrs = {"class": "tinymce-editor", "rows": 24}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    class Media:
        js = (
            "dist/tinymce/tinymce.min.js",
            "js/tinymce-init.js",
        )


class StaticPageAdminForm(forms.ModelForm):
    class Meta:
        model = StaticPage
        fields = ("title", "slug", "content_html", "is_published")
        widgets = {"content_html": TinyMCETextarea()}


class PageMediaInline(admin.TabularInline):
    model = PageMedia
    extra = 1
    fields = ("file", "alt_text")

    def has_add_permission(self, request, obj=None):
        return is_platform_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_platform_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_platform_admin(request.user)


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    form = StaticPageAdminForm
    inlines = [PageMediaInline]
    list_display = ("title", "slug", "is_published", "updated_at", "updated_by")
    list_filter = ("is_published",)
    search_fields = ("title", "slug")
    readonly_fields = ("updated_at", "updated_by", "preview_link")
    prepopulated_fields = {"slug": ("title",)}

    def preview_link(self, obj):
        if obj.pk and obj.is_published:
            return format_html('<a href="/seite/{}/" target="_blank">Vorschau</a>', obj.slug)
        return "–"

    preview_link.short_description = "Vorschau"

    def has_module_permission(self, request):
        return is_platform_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_platform_admin(request.user)

    def has_add_permission(self, request):
        return is_platform_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_platform_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_platform_admin(request.user)

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display

from .models import Contact, SiteInfo, About, AboutImage
from .resources import ContactResource, SiteInfoResource, AboutResource, AboutImageResource


@admin.register(Contact)
class ContactAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = ContactResource

    list_display = (
        "user_name",
        "email",
        "phone",
        "subject_badge",
        "short_message",
        "created_date",
    )
    list_filter = ("subject", "created_date")
    search_fields = ("user_name", "email", "phone", "message")
    readonly_fields = ("created_date",)
    date_hierarchy = "created_date"
    list_per_page = 20
    ordering = ("-created_date",)

    fieldsets = (
        (_("Contact Info"), {
            "fields": ("user_name", "email", "phone")
        }),
        (_("Message Info"), {
            "fields": ("subject", "message", "created_date")
        }),
    )

    @display(description=_("Subject"))
    def subject_badge(self, obj):
        colors = {
            "1": "blue",
            "2": "red",
            "3": "orange",
            "4": "green",
            "5": "gray",
        }
        labels = dict(Contact.SubjectChoices.choices)
        color = colors.get(obj.subject, "gray")
        return format_html(
            '<span style="padding:4px 10px;border-radius:999px;background:{};color:white;">{}</span>',
            color,
            labels.get(obj.subject, obj.subject),
        )

    @display(description=_("Message"))
    def short_message(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message


@admin.register(SiteInfo)
class SiteInfoAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = SiteInfoResource

    list_display = ("id","email", "phone", "address")
    search_fields = ("email", "phone", "address")
    readonly_fields = ("preview_links",)
    fieldsets = (
        (_("Basic Info"), {
            "fields": ("email", "phone", "address")
        }),
        (_("Social Links"), {
            "fields": (
                "telegram",
                "instagram",
                "facebook",
                "twitter",
                "whatsapp",
            )
        }),
        (_("Address"), {
            "fields": ("address_url",)
        }),
        (_("Working Hours"), {
            "fields": ("working_hours",)
        }),
        (_("Preview"), {
            "fields": ("preview_links",)
        }),
    )

    @display(description=_("Links"))
    def preview_links(self, obj):
        if not obj.pk:
            return _("Save first to preview links.")
        return format_html(
            '<a href="{}" target="_blank">Telegram</a> | '
            '<a href="{}" target="_blank">Instagram</a> | '
            '<a href="{}" target="_blank">Facebook</a> | '
            '<a href="{}" target="_blank">Twitter</a> | '
            '<a href="{}" target="_blank">Whatsapp</a>',
            obj.telegram, obj.instagram, obj.facebook, obj.twitter, obj.whatsapp
        )


class AboutImageInline(TabularInline):
    model = AboutImage
    resource_class = AboutImageResource
    extra = 0
    fields = ("title", "image")
    show_change_link = True


@admin.register(About)
class AboutAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = AboutResource

    list_display = ("title", "short_description", "created_date", "poster_preview")
    search_fields = ("title", "description", "text")
    readonly_fields = ("created_date", "poster_preview")
    inlines = [AboutImageInline]
    list_per_page = 20
    ordering = ("-created_date",)

    fieldsets = (
        (_("Main"), {
            "fields": ("title", "description", "text", "poster_image", "poster_preview")
        }),
        (_("Meta"), {
            "fields": ("created_date",)
        }),
    )

    @display(description=_("Description"))
    def short_description(self, obj):
        return obj.description[:60] + "..." if obj.description and len(obj.description) > 60 else obj.description

    @display(description=_("Poster"))
    def poster_preview(self, obj):
        if obj.poster_image:
            return format_html('<img src="{}" style="max-height:80px;border-radius:8px;" />', obj.poster_image.url)
        return _("No image")


# @admin.register(AboutImage)
# class AboutImageAdmin(ImportExportModelAdmin, ModelAdmin):
#     resource_class = AboutImageResource

#     list_display = ("title", "about", "image_preview")
#     search_fields = ("title", "about__title")
#     list_filter = ("about",)
#     list_select_related = ("about",)
#     fields = ("about", "title", "image", "image_preview")
#     readonly_fields = ("image_preview",)
#     autocomplete_fields = ("about",)

#     @display(description=_("Image"))
#     def image_preview(self, obj):
#         if obj.image:
#             return format_html('<img src="{}" style="max-height:80px;border-radius:8px;" />', obj.image.url)
#         return _("No image")

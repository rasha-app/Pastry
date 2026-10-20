from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display
from import_export.admin import ImportExportModelAdmin

from .models import (
    Tag, Ingredient, Category, Product, ProductImage,
    ProductVariant, CustomizationOption, CustomizationValue,
)


# ---------- Inlines ----------

class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "title")
    tab = True


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("variant_type", "title", "image", "extra_price", "is_active")
    readonly_fields = ("value",)
    tab = True


class CustomizationValueInline(TabularInline):
    model = CustomizationValue
    extra = 1
    fields = ("title", "image", "extra_price", "is_active")
    tab = True


class CustomizationOptionInline(StackedInline):
    model = CustomizationOption
    extra = 1
    fields = ("group_title", "option_type", "is_required", "min_select", "max_select")
    show_change_link = True
    tab = True


# ---------- Admins ----------

@admin.register(Tag)
class TagAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ("id", "title")
    search_fields = ("title",)
    ordering = ("title",)


@admin.register(Ingredient)
class IngredientsAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ("id", "title")
    search_fields = ("title",)
    ordering = ("title",)


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ("id", "title", "parent", "is_active", "created_date")
    list_filter = ("is_active", "parent")
    search_fields = ("title", "description")
    autocomplete_fields = ("parent",)
    prepopulated_fields = {"meta_title": ("title",)} if False else {}
    fieldsets = (
        (_("Main"), {"fields": ("title", "description", "parent", "is_active")}),
        (_("SEO"), {"fields": ("meta_title",), "classes": ("collapse",)}),
    )


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = (
        "id", "title", "category", "base_price",
        "final_price_display", "stock_quantity",
        "is_available", "is_published", "created_date",
    )
    list_filter = ("is_published", "is_available", "is_customizable", "category", "tags")
    search_fields = ("title", "slug", "description", "text")
    readonly_fields = ("slug", "discount_price", "created_date", "modified_date")
    autocomplete_fields = ("category", "tags", "ingredients")
    inlines = [
        ProductImageInline,
        ProductVariantInline,
        CustomizationOptionInline,
    ]
    fieldsets = (
        (_("Main"), {
            "fields": ("category", "title", "slug", "description", "text",
                       "main_image", "is_published", "is_available", "is_customizable")
        }),
        (_("Relations"), {"fields": ("tags", "ingredients")}),
        (_("Price & Discount"), {
            "fields": ("base_price", "discount_percent", "discount_price", "discount_expires_date")
        }),
        (_("Stock"), {"fields": ("stock_quantity", "min_order_quantity", "max_order_quantity")}),
        (_("Physical"), {
            "fields": ("weight_grams", "height", "width", "length",
                       "preparation_time", "shelf_life_hours",
                       "is_perishable", "requires_refrigeration")
        }),
        (_("SEO & Meta"), {"fields": ("meta_title", "created_date", "modified_date"),
                           "classes": ("collapse",)}),
    )

    @display(description=_("Final Price"))
    def final_price_display(self, obj):
        return obj.final_price

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("tags", "ingredients")


@admin.register(ProductImage)
class ProductImageAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ("id", "product", "title")
    search_fields = ("product__title", "title")
    autocomplete_fields = ("product",)


@admin.register(ProductVariant)
class ProductVariantAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ("id", "product", "variant_type", "title", "value", "extra_price", "is_active")
    list_filter = ("variant_type", "is_active")
    search_fields = ("product__title", "title", "value")
    autocomplete_fields = ("product",)


@admin.register(CustomizationOption)
class CustomizationOptionAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ("id", "product", "group_title", "option_type", "is_required", "min_select", "max_select")
    list_filter = ("option_type", "is_required")
    search_fields = ("product__title", "group_title")
    autocomplete_fields = ("product",)
    inlines = [CustomizationValueInline]


@admin.register(CustomizationValue)
class CustomizationValueAdmin(ImportExportModelAdmin, ModelAdmin):
    list_display = ("id", "option", "title", "extra_price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("option__group_title", "title")
    autocomplete_fields = ("option",)
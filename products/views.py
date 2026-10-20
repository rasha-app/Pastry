
import logging

from django.db.models.query import Prefetch, QuerySet
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import ListView,DetailView,DeleteView,UpdateView,CreateView
from django.views.generic.edit import ModelFormMixin
from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin
from dal_alight.views import AlightQuerySetView
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from django.contrib import messages


from .models import Category, CustomizationOption, CustomizationValue, Product, ProductImage, ProductVariant, Tag, Ingredient

logger = logging.getLogger(__name__)


class TagAutocomplete(LoginRequiredMixin, AlightQuerySetView):
    # dal_alight با create_field گزینه «Create "..."» نشان می‌دهد و با POST همان‌جا می‌سازد؛
    # پس data-tags لازم نیست. iexact هم تا «Cake» و «cake» دکمه Create جدا نگیرند.
    create_field = "title"
    validate_create = True
    search_fields = ["title"]

    def has_add_permission(self, request):
        # GET برای همه لاگین‌کرده‌ها؛ POST (ساخت تگ جدید) فقط staff تا هرکسی تگ نسازد
        if request.method == "POST":
            return request.user.is_staff and super().has_add_permission(request)
        return True

    def get_queryset(self):
        qs = Tag.objects.all().order_by("title")
        if self.q:
            qs = qs.filter(title__icontains=self.q)
        return qs[:30]

    def get_result_label(self, item):
        return item.title

    def get_selected_result_label(self, item):
        return item.title

    def create_object(self, text):
        text = (text or "").strip()
        if not text:
            from django.core.exceptions import ValidationError
            raise ValidationError(_("Title cannot be empty."))
        obj = Tag.objects.filter(title__iexact=text).first()
        if obj is not None:
            return obj
        if len(text) > 100:
            from django.core.exceptions import ValidationError
            raise ValidationError(_("Value too long: %(v)s") % {"v": text})
        return Tag.objects.create(title=text)


class IngredientAutocomplete(LoginRequiredMixin, AlightQuerySetView):
    create_field = "title"
    validate_create = True
    search_fields = ["title"]

    def has_add_permission(self, request):
        if request.method == "POST":
            return request.user.is_staff and super().has_add_permission(request)
        return True

    def get_queryset(self):
        qs = Ingredient.objects.all().order_by("title")
        if self.q:
            qs = qs.filter(title__icontains=self.q)
        return qs[:30]

    def get_result_label(self, item):
        return item.title

    def get_selected_result_label(self, item):
        return item.title

    def create_object(self, text):
        text = (text or "").strip()
        if not text:
            from django.core.exceptions import ValidationError
            raise ValidationError(_("Title cannot be empty."))
        obj = Ingredient.objects.filter(title__iexact=text).first()
        if obj is not None:
            return obj
        if len(text) > 100:
            from django.core.exceptions import ValidationError
            raise ValidationError(_("Value too long: %(v)s") % {"v": text})
        return Ingredient.objects.create(title=text)

class TagDetailView(ListView):
    template_name = 'products_list.html'
    model = Tag
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        self.tag = get_object_or_404(Tag,pk=self.kwargs['pk'])
        return Product.objects.filter(is_published=True,tags=self.tag).only(
                    'id','category_id','title','slug','description',
                    'base_price','discount_price','discount_percent','main_image',
                ).order_by('title')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.tag.title
        context["op"] = 'tag'

        return context

class CategoryDetailView(ListView):
    template_name = 'products_list.html'
    model = Product
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        self.category = get_object_or_404(Category, id=self.kwargs['pk'], is_active=True)
        return Product.objects.filter(
            is_published=True, category=self.category
        ).only(
            'id', 'category_id', 'title', 'slug', 'description',
            'base_price', 'discount_price', 'discount_percent', 'main_image',
        ).order_by('title')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.category.title
        context['op'] = 'category'
        return context
    
class ProductsListView(ListView):
    template_name = 'products_list.html'
    model = Product
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        qs = Product.objects.filter(is_published=True).only(
            'id', 'category_id', 'title', 'slug', 'description',
            'base_price', 'discount_price', 'discount_percent', 'main_image',
        ).order_by('-created_date')
        return qs

class ProductDetailView(DetailView):
    template_name = 'product_detail.html'
    model = Product
    context_object_name = 'product'
    queryset = Product.objects.filter(is_published=True)

    def get_object(self, queryset=None):
        # اسلاگ اشتباه → 404 (جلوگیری از محتوای تکراری سئو)
        if queryset is None:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs['pk'], slug=self.kwargs.get('slug'))

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related('category').prefetch_related(
            'tags','ingredients',
            Prefetch('images',queryset=ProductImage.objects.all()),
            Prefetch('variants',queryset=ProductVariant.objects.filter(is_active=True)),
            Prefetch('options',queryset=CustomizationOption.objects.all().prefetch_related(
                Prefetch('values',CustomizationValue.objects.filter(is_active=True))
            )),
        )
        return qs


# class CreateProductView(LoginRequiredMixin,UserPassesTestMixin,CreateView):
#     template_name = 'crud.html'
#     form_class  = ProductCreateForm
#     model=Product
#     success_url = reverse_lazy('products_list')

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context["title"] = _('Create New Product')
#         return context
    
#     def form_valid(self, form):
#         form.save()
#         messages.info(self.request,_("New product successfully registered."))
#         logger.info("New product successfully registered.")
#         return super().form_valid(form) 

#     def form_invalid(self, form):
#         error_messages = []
#         for field_errors in form.errors.values():
#             for error in field_errors:
#                 error_messages.append(error)
#         messages.warning(self.request, _(f"Form errors: {', '.join(error_messages)}"))
#         logger.error(f"Form Error: {error_messages}")

#         # Ø§Ø¶Ø§ÙÙ‡ Ú©Ø±Ø¯Ù† ÙØ±Ù…â€ŒØ³Øª Ø¨Ø¯Ù†Ù‡ Ø¨Ù‡ context Ø¯Ø± ØµÙˆØ±Øª Ø®Ø·Ø§
#         context = self.get_context_data(form=form)
#         return self.render_to_response(self.get_context_data(**context))
    
#     def test_func(self):
#         return bool(self.request.user.is_staff)
# --- Product CRUD (nested formsets) ---
from django.db import transaction
from .forms import ProductForm
from .forms import ProductImageFormSet, ProductVariantFormSet
from .forms import CustomizationOptionFormSet, CustomizationValueFormSet

def build_value_formsets(option_formset, data=None, files=None):
    out = []
    for opt_form in option_formset.forms:
        prefix = f"values-{opt_form.prefix}"
        kw = {"instance": opt_form.instance, "prefix": prefix}
        if data is not None:
            fs = CustomizationValueFormSet(data, files, **kw)
        else:
            fs = CustomizationValueFormSet(**kw)
        out.append(fs)
    return out

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff # type: ignore

class ProductFormsetMixin:
    template_name = "crud.html"
    def get_formsets(self, inst):
        img = ProductImageFormSet(instance=inst, prefix="images")
        var = ProductVariantFormSet(instance=inst, prefix="variants")
        opt = CustomizationOptionFormSet(instance=inst, prefix="options")
        vals = build_value_formsets(opt)
        return img, var, opt, vals
    def get_bound_formsets(self, inst):
        img = ProductImageFormSet(self.request.POST, self.request.FILES, instance=inst, prefix="images") # type: ignore
        var = ProductVariantFormSet(self.request.POST, self.request.FILES, instance=inst, prefix="variants") # type: ignore
        opt = CustomizationOptionFormSet(self.request.POST, self.request.FILES, instance=inst, prefix="options") # type: ignore
        vals = build_value_formsets(opt, self.request.POST, self.request.FILES) # type: ignore
        return img, var, opt, vals
    def all_valid(self, img, var, opt, vals):
        ok = img.is_valid() and var.is_valid() and opt.is_valid()
        for opt_form, vf in zip(opt.forms, vals):
            # آپشن حذف‌شده: ولیوهایش چک نشوند
            cd = getattr(opt_form, "cleaned_data", None) or {}
            if cd.get("DELETE"):
                continue
            ok = vf.is_valid() and ok
        return ok

class ProductCreateView(StaffRequiredMixin, ProductFormsetMixin, CreateView):
    model = Product
    form_class = ProductForm
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            img, var, opt, vals = self.get_bound_formsets(Product())
            ctx["image_formset"] = img
            ctx["variant_formset"] = var
            ctx["option_formset"] = opt
            ctx["value_formsets"] = vals
            ctx["option_value_pairs"] = list(zip(opt.forms, vals))
        else:
            img, var, opt, vals = self.get_formsets(Product())
            ctx["image_formset"] = img
            ctx["variant_formset"] = var
            ctx["option_formset"] = opt
            ctx["value_formsets"] = vals
            ctx["option_value_pairs"] = list(zip(opt.forms, vals))
            ctx["title"] = _("Create Product")
        return ctx
    def form_valid(self, form):
        image_fs, variant_fs, option_fs, value_fss = self.get_bound_formsets(form.instance)
        if not self.all_valid(image_fs, variant_fs, option_fs, value_fss):
            messages.warning(self.request, _("Please correct the errors below."))
            ctx = self.get_context_data(form=form)
            ctx["image_formset"] = image_fs
            ctx["variant_formset"] = variant_fs
            ctx["option_formset"] = option_fs
            ctx["value_formsets"] = value_fss
            ctx["option_value_pairs"] = list(zip(option_fs.forms, value_fss))
            return self.render_to_response(ctx)
        try:
            with transaction.atomic():
                self.object = form.save()
                image_fs.instance = self.object
                variant_fs.instance = self.object
                option_fs.instance = self.object
                image_fs.save()
                variant_fs.save()
                option_fs.save()
                for opt_form, val_fs in zip(option_fs.forms, value_fss):
                    if opt_form.cleaned_data.get("DELETE"):
                        continue
                    val_fs.instance = opt_form.instance
                    val_fs.save()
        except Exception as e:
            logger.exception("Product create failed: %s", e)
            messages.error(self.request, _("Save failed."))
            ctx = self.get_context_data(form=form)
            return self.render_to_response(ctx)
        messages.success(self.request, _("Product created successfully."))
        return super(ModelFormMixin, self).form_valid(form) # type: ignore
    def get_success_url(self):
        return self.object.get_absolute_url()

class ProductUpdateView(StaffRequiredMixin, ProductFormsetMixin, UpdateView):
    model = Product
    form_class = ProductForm
    def get_queryset(self):
        return Product.objects.prefetch_related("tags","ingredients","images","variants","options__values")
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            img, var, opt, vals = self.get_bound_formsets(self.object)
            ctx["image_formset"] = img
            ctx["variant_formset"] = var
            ctx["option_formset"] = opt
            ctx["value_formsets"] = vals
            ctx["option_value_pairs"] = list(zip(opt.forms, vals))
        else:
            img, var, opt, vals = self.get_formsets(self.object)
            ctx["image_formset"] = img
            ctx["variant_formset"] = var
            ctx["option_formset"] = opt
            ctx["value_formsets"] = vals
            ctx["option_value_pairs"] = list(zip(opt.forms, vals))
            ctx["title"] = _("Edit Product")
        return ctx
    def form_valid(self, form):
        image_fs, variant_fs, option_fs, value_fss = self.get_bound_formsets(self.object)
        if not self.all_valid(image_fs, variant_fs, option_fs, value_fss):
            messages.warning(self.request, _("Please correct the errors below."))
            ctx = self.get_context_data(form=form)
            ctx["image_formset"] = image_fs
            ctx["variant_formset"] = variant_fs
            ctx["option_formset"] = option_fs
            ctx["value_formsets"] = value_fss
            ctx["option_value_pairs"] = list(zip(option_fs.forms, value_fss))
            return self.render_to_response(ctx)
        try:
            with transaction.atomic():
                self.object = form.save()
                image_fs.save()
                variant_fs.save()
                option_fs.save()
                for opt_form, val_fs in zip(option_fs.forms, value_fss):
                    if opt_form.cleaned_data.get("DELETE"):
                        continue
                    val_fs.instance = opt_form.instance
                    val_fs.save()
        except Exception as e:
            logger.exception("Product update failed: %s", e)
            messages.error(self.request, _("Save failed."))
            ctx = self.get_context_data(form=form)
            return self.render_to_response(ctx)
        messages.success(self.request, _("Product updated successfully."))
        return super(ModelFormMixin, self).form_valid(form) # type: ignore
    def get_success_url(self):
        return self.object.get_absolute_url()

class ProductDeleteView(StaffRequiredMixin, DeleteView):
    model = Product
    template_name = "crud.html"
    success_url = reverse_lazy("products_list")
    context_object_name = "product"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Delete Product")
        ctx["is_delete"] = True
        return ctx
    def form_valid(self, form):
        messages.success(self.request, _("Product deleted."))
        with transaction.atomic():
            return super().form_valid(form) # type: ignore

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from dal_alight.widgets import ModelAlightMultiple

from cores.image_utils import compress_image_file

from .models import Product, ProductImage, ProductVariant
from .models import CustomizationOption, CustomizationValue, Tag, Ingredient


class TaggingModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """مقادیر dal_alight همیشه pk هستند (تگ جدید با POST همان‌جا ساخته و pk می‌گیرد).
    این فیلد برای سازگاری به عقب، اگر رشته غیرعددی آمد (مثلاً POST دستی یا new_*)،
    آن را نگه می‌دارد تا در save() ساخته شود — نه در clean() تا رکورد یتیم نماند."""

    def clean(self, value):
        if not value:
            self._pending_names = []
            return super().clean([])
        pks, pending = [], []
        str_vals, num_ids = [], []
        for v in value:
            s = str(v).strip()
            if not s:
                continue
            if s.isdigit():
                num_ids.append(int(s))
            else:
                str_vals.append(s)
        # یک کوئری برای همه pkها (به‌جای N کوئری exists)
        existing_ids = set(self.queryset.filter(pk__in=num_ids).values_list("pk", flat=True)) if num_ids else set()  # type: ignore
        pks.extend(str(i) for i in num_ids if i in existing_ids)
        # رشته‌ها: iexact تکی با یک کوئری
        for s in str_vals:
            obj = self.queryset.filter(title__iexact=s).first()  # type: ignore
            if obj is not None:
                pks.append(str(obj.pk))
                continue
            if len(s) > 100:
                raise ValidationError(_("Value too long: %(v)s") % {"v": s})
            pending.append(s)
        self._pending_names = pending
        return super().clean(pks)


def parse_comma_names(raw):
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):  # clean_* لیست برمی‌گرداند؛ POST بعدی رشته است
        out = []
        for item in raw:
            out.extend(parse_comma_names(str(item)))
        return out
    raw = str(raw).replace("،", ",")
    return [p.strip() for p in raw.split(",") if p.strip()]

class ProductForm(forms.ModelForm):
    tags = TaggingModelMultipleChoiceField(
        queryset=Tag.objects.all(), required=False, label=_("Tags"),
        widget=ModelAlightMultiple(
            url="tag_autocomplete",
            attrs={"data-placeholder": _("Search or create tags…"),
                   "style": "width:100%"}))
    ingredients = TaggingModelMultipleChoiceField(
        queryset=Ingredient.objects.all(), required=False, label=_("Ingredients"),
        widget=ModelAlightMultiple(
            url="ingredient_autocomplete",
            attrs={"data-placeholder": _("Search or create ingredients…"),
                   "style": "width:100%"}))
    new_tags = forms.CharField(required=False, label=_("New tags"),
        help_text=_("Or type comma-separated here. e.g: sweet, birthday"),
        widget=forms.TextInput(attrs={"placeholder": "tag1, tag2"}))
    new_ingredients = forms.CharField(required=False, label=_("New ingredients"),
        help_text=_("Or type comma-separated here."),
        widget=forms.TextInput(attrs={"placeholder": "flour, sugar"}))
    class Meta:
        model = Product
        fields = ["category","title","description","text",
            "is_published","is_available","is_customizable",
            "tags","ingredients","base_price","discount_percent",
            "discount_expires_date","stock_quantity","min_order_quantity",
            "max_order_quantity","weight_grams","height","width","length",
            "preparation_time","shelf_life_hours","is_perishable",
            "requires_refrigeration","main_image","meta_title"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "text": forms.Textarea(attrs={"rows": 4}),
            "discount_expires_date": forms.DateTimeInput(attrs={"type": "datetime-local"})
            }

    def clean_main_image(self):
        return compress_image_file(
            self.cleaned_data.get("main_image"),
            max_size_mb=0.5, max_dimension=1920, quality=75, threshold_kb=300,
        )
        
    # def clean_slug(self):
    #     slug = (self.cleaned_data.get("slug") or "").strip()
    #     if not slug:
    #         return ""
    #     qs = Product.objects.filter(slug=slug)
    #     if self.instance.pk:
    #         qs = qs.exclude(pk=self.instance.pk)
    #     if qs.exists():
    #         raise ValidationError(_("This slug is already taken."))
    #     return slug
    
    def clean_new_tags(self):
        names = parse_comma_names(self.cleaned_data.get("new_tags",""))
        if len(names) > 30:
            raise ValidationError(_("Too many new tags (max 30)."))
        for n in names:
            if len(n) > 100:
                raise ValidationError(_("Tag too long: %(v)s") % {"v": n})
        return names
    
    def clean_new_ingredients(self):
        names = parse_comma_names(self.cleaned_data.get("new_ingredients",""))
        if len(names) > 30:
            raise ValidationError(_("Too many new ingredients."))
        return names
    
    def save(self, commit=True):
        # NOTE: فیلد slug در Meta.fields نیست (کامنت شده) پس به
        # cleaned_data دست نمی‌زنیم؛ ساخت slug با متد Product.save() است.
        # دست‌کاری قبلی (`self.instance.slug = ""`) در حالت ویرایش،
        # اسلاگ موجود را پاک و لینک محصول را می‌شکست.
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            self._save_pending_taggings(instance)
        return instance

    def _save_pending_taggings(self, instance):
        """رشته‌های دستی (fallback) + فیلدهای new_* را اینجا می‌سازیم.
        در حالت عادی dal_alight تگ جدید را همان لحظه با POST می‌سازد و pk می‌فرستد،
        پس pending معمولاً خالی است."""
        from django.db import transaction, IntegrityError
        for field_name, rel_name, model in (
            ("tags", "tags", Tag),
            ("ingredients", "ingredients", Ingredient),
        ):
            field = self.fields.get(field_name)
            pending = list(getattr(field, "_pending_names", []) or [])
            # new_tags/new_ingredients کاما-جدا هم با همین مسیر می‌آید
            extra_raw = self.cleaned_data.get(
                "new_tags" if field_name == "tags" else "new_ingredients") or []
            pending.extend(parse_comma_names(extra_raw))
            for name in dict.fromkeys([n.strip() for n in pending if n.strip()]):
                # get_or_create اتمیک تا زیر بار همزمان تگ تکراری نسازد
                try:
                    with transaction.atomic():
                        obj, _ = model.objects.get_or_create(title=name)
                except IntegrityError:
                    # ریس: همزمان ساخته شده → همان را بگیر (iexact برای ی/ک عربی)
                    obj = model.objects.filter(title__iexact=name).first() or model.objects.filter(title=name).first()
                if obj is None:
                    continue
                getattr(instance, rel_name).add(obj)


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "title"]

    def clean_image(self):
        return compress_image_file(
            self.cleaned_data.get("image"),
            max_size_mb=0.5, max_dimension=1920, quality=75, threshold_kb=300,
        )

class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["variant_type","title","image","extra_price","is_active"]

    def clean_image(self):
        return compress_image_file(
            self.cleaned_data.get("image"),
            max_size_mb=0.5, max_dimension=1920, quality=75, threshold_kb=300,
        )

class CustomizationOptionForm(forms.ModelForm):
    class Meta:
        model = CustomizationOption
        fields = ["group_title","option_type","is_required","min_select","max_select"]

class CustomizationValueForm(forms.ModelForm):
    class Meta:
        model = CustomizationValue
        fields = ["title","image","extra_price","is_active"]

    def clean_image(self):
        return compress_image_file(
            self.cleaned_data.get("image"),
            max_size_mb=0.5, max_dimension=1920, quality=75, threshold_kb=300,
        )

class BaseVariantFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        from .models import normalize_fa
        seen = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if not form.has_changed():
                continue
            cd = form.cleaned_data
            if cd.get("DELETE"):
                continue
            title = normalize_fa(cd.get("title") or "")
            if not cd.get("variant_type") and not title:
                continue
            key = (str(cd.get("variant_type") or "").strip(), title)
            if key in seen:
                raise ValidationError(_("Duplicate variant in this form."))
            seen.add(key)

class BaseValueFormSet(BaseInlineFormSet):
    pass

class BaseOptionFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            cd = form.cleaned_data
            if cd.get("DELETE"):
                continue
            gt = str(cd.get("group_title") or "").strip()
            if not gt:
                continue
            if gt in seen:
                raise ValidationError(_("Duplicate option group_title."))
            seen.add(gt)

ProductImageFormSet = inlineformset_factory(Product, ProductImage,
    form=ProductImageForm, extra=1, can_delete=True)
ProductVariantFormSet = inlineformset_factory(Product, ProductVariant,
    form=ProductVariantForm, formset=BaseVariantFormSet, extra=1, can_delete=True)
CustomizationOptionFormSet = inlineformset_factory(Product, CustomizationOption,
    form=CustomizationOptionForm, formset=BaseOptionFormSet, extra=1, can_delete=True)
CustomizationValueFormSet = inlineformset_factory(CustomizationOption, CustomizationValue,
    form=CustomizationValueForm, formset=BaseValueFormSet, extra=1, can_delete=True)

from pathlib import Path
import random,uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator

from django.core.exceptions import ValidationError
import jdatetime

def validate_image(file):
    max_size = 1000 * 1024  # 1000 KB
    valid_extensions = ["jpg", "jpeg", "png", "webp"]

    extension = Path(file.name).suffix.lower().replace(".", "")
    if extension not in valid_extensions:
        raise ValidationError( _("Valid formats are: JPG, JPEG, PNG and WEBP."))

    if file.size > max_size:
        raise ValidationError( _("File size must be less than 1000 KB."))

def normalize_fa(text):
    """Normalize Persian text for uniqueness key: strip, unify ي/ي ک/ك, remove ZWNJ dup spaces."""
    if not text:
        return ""
    s = str(text).strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    s = " ".join(s.split())
    return s

def upload_to_name(instance, filename):
    model_name = instance.__class__.__name__.lower()
    extension = Path(filename).suffix.lower()

    new_filename = slugify(Path(filename).stem)
    if not new_filename:
        new_filename = uuid.uuid4().hex

    dt = timezone.now().date()
    jalali = jdatetime.date.fromgregorian(date=dt)

    return f'{model_name}/{jalali.year}-{jalali.month}-{jalali.day}/{new_filename}{extension}'
    


class ProductBaseMixin(models.Model):
    meta_title = models.CharField(max_length=255, blank=True, null=True,verbose_name=_("Meta Title"))
    # meta_description = models.TextField(blank=True, null=True,verbose_name=_("Meta Description"))
    created_date = models.DateTimeField(auto_now_add=True,verbose_name=_("Created Date"))

    class Meta:
        abstract = True

class Tag(models.Model):
    title = models.CharField(max_length=100,unique=True,verbose_name=_("Title"))
    # products

    def __str__(self):
        return self.title
    
    class Meta:
        db_table = "tag"
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

class Ingredient(models.Model): # مواد استفاده شده
    title = models.CharField(max_length=100,unique=True,verbose_name=_("Title"))
    # products

    def __str__(self):
        return self.title
    
    class Meta:
        db_table = "ingredients"
        verbose_name = _("Ingredients")
        verbose_name_plural = _("Ingredients")
        
class Category(ProductBaseMixin):
    title = models.CharField(max_length=100,verbose_name=_("Title"))
    description = models.TextField(max_length=250,blank=True, null=True,verbose_name=_("Description"))
    parent = models.ForeignKey('self',on_delete=models.PROTECT,related_name="categories",blank=True,null=True,verbose_name=_("Parent"))
    is_active       = models.BooleanField(default=True,verbose_name=_("Is Active"))
    # products

    def __str__(self):
        return self.title
    # در Category:

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["slug"])
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.parent is None:
            qs = Category.objects.filter(title=self.title, parent__isnull=True)
        else:
            qs = Category.objects.filter(title=self.title, parent=self.parent)
        qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(_("A category with this name exists in this parent."))
    
    class Meta:
        db_table = "category"
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        constraints = [
            models.UniqueConstraint(fields=["title", "parent"], name="unique_category_per_parent"),
        ]

class Product(ProductBaseMixin):
    # user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name="%(class)s",verbose_name=_("User"))
    category    = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products",verbose_name=_("Category"))
    title       = models.CharField(max_length=200,verbose_name=_("Title"))
    slug        = models.SlugField(max_length=250,unique=True,allow_unicode=True,verbose_name=_("Slug"))
    description = models.TextField(max_length=300,blank=True, null=True,verbose_name=_("Description"))
    text        = models.TextField(max_length=1000,blank=True, null=True,verbose_name=_("Text"))
    is_published= models.BooleanField(default=True,verbose_name=_("Is Published"))
    tags        = models.ManyToManyField(Tag,blank=True,related_name="products",verbose_name=_("Tags"))
    ingredients = models.ManyToManyField(Ingredient,blank=True,verbose_name=_("Ingredients"))
    base_price  = models.DecimalField(max_digits=10, decimal_places=0,verbose_name=_("Base Price"))
    discount_price  = models.DecimalField(max_digits=10,decimal_places=0,blank=True,null=True,verbose_name=_("Discount Price")) # type: ignore
    discount_percent= models.PositiveSmallIntegerField(blank=True,null=True,validators=[MinValueValidator(1), MaxValueValidator(100)],verbose_name=_("Discount Percent"))
    discount_expires_date= models.DateTimeField(blank=True,null=True,verbose_name=_("Discount Expires Date"))
    stock_quantity  = models.PositiveIntegerField(blank=True,null=True,verbose_name=_("Stock Quantity"))
    min_order_quantity  = models.PositiveSmallIntegerField(default=1,verbose_name=_("Min Order Quantity"))
    max_order_quantity  = models.PositiveSmallIntegerField(default=5,verbose_name=_("Max Order Quantity"))
    weight_grams    = models.PositiveSmallIntegerField(default=1,verbose_name=_("Weight Grams"))
    height          = models.PositiveSmallIntegerField(default=1,verbose_name=_("Height"))
    width           = models.PositiveSmallIntegerField(default=1,verbose_name=_("Width"))
    length          = models.PositiveSmallIntegerField(default=1,verbose_name=_("Length"))
    preparation_time= models.PositiveSmallIntegerField(default=120,verbose_name=_("Preparation Time 'Minutes'"))
    shelf_life_hours= models.PositiveSmallIntegerField(default=1,verbose_name=_("Shelf Life 'Hours'"))
    is_perishable   = models.BooleanField(default=True,verbose_name=_("Is Perishable"))
    requires_refrigeration   = models.BooleanField(default=True,verbose_name=_("Requires Refrigeration"))
    main_image      = models.ImageField(upload_to=upload_to_name,validators=[validate_image],blank=True,null=True,verbose_name=_("Main Image"))
    is_customizable = models.BooleanField(default=False,verbose_name=_("Is Customizable"))
    is_available    = models.BooleanField(default=True,verbose_name=_("Is Available"))
    modified_date   = models.DateTimeField(auto_now=True,verbose_name=_("Modified Date"))

    # images
    # variants
    # options

    def clean(self):
        super().clean()
        if (self.min_order_quantity and self.max_order_quantity
            and self.min_order_quantity > self.max_order_quantity):
            raise ValidationError(_("min_order_quantity cannot be greater than max_order_quantity."))
        if self.discount_percent and not (1 <= self.discount_percent <= 100):
            raise ValidationError(_("discount_percent must be between 1 and 100."))
        

    @property
    def final_price(self):
        if not self.discount_price:
            return self.base_price
        if self.discount_expires_date and self.discount_expires_date <= timezone.now():
            return self.base_price
        return self.discount_price

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            slug = base_slug
            while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{random.randint(1000, 99999)}"
            self.slug = slug

        if self.discount_percent and 0 < self.discount_percent <= 100:
            if self.discount_percent == 100:
                self.discount_price = Decimal("0")
            else:
                self.discount_price = (
                    self.base_price - (self.base_price * Decimal(self.discount_percent) / Decimal(100))
                ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        else:
            self.discount_price = None
            self.discount_percent = None

        self.full_clean(exclude=["slug"])  # اضافه شد
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"pk": self.pk , 'slug':self.slug})
    
    
    class Meta:
        db_table = "product"
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images",verbose_name=_("Product"))
    image = models.ImageField(upload_to=upload_to_name,validators=[validate_image],blank=True,null=True,verbose_name=_("Image"))
    title = models.CharField(max_length=150,blank=True,null=True,verbose_name=_("Title"))

    def __str__(self):
        return f'{self.product} - {self.title}'
    
    class Meta:
        db_table = "product_image"
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")

class ProductVariant(models.Model):
    class VariantChoices(models.TextChoices):
        Size      = 'size'    ,_('Size')
        Flavor    = 'flavor'  ,_('Flavor')
        Color     = 'color'   ,_('Color')
        Weight    = 'weight'  ,_('Weight')
        Shape     = 'shape'   ,_('Shape')
        
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name="variants",verbose_name=_("Product"))
    variant_type = models.CharField(max_length=10,choices=VariantChoices,default=VariantChoices.Size,verbose_name=_("Variant Type"))
    title   = models.CharField(max_length=100,verbose_name=_("Title"))
    value   = models.CharField(max_length=100,blank=True,editable=False,verbose_name=_("value"))
    image   = models.ImageField(upload_to=upload_to_name,validators=[validate_image],blank=True,null=True,verbose_name=_("Image"))
    extra_price  = models.DecimalField(max_digits=10, decimal_places=0,default=0,verbose_name=_("Extra Price")) # type: ignore
    is_active       = models.BooleanField(default=True,verbose_name=_("Is Active"))

    def clean(self):
        super().clean()
        if not (self.title or "").strip():
            raise ValidationError({"title": _("Title cannot be empty.")})
        self.value = normalize_fa(self.title)[:100]

    def save(self, *args, **kwargs):
        if self.title:
            self.value = normalize_fa(self.title)[:100]
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product} - {self.get_variant_type_display()} - {self.title}' # type: ignore

    class Meta:
        db_table = "product_variant"
        verbose_name = _("Product Variant")
        verbose_name_plural = _("Product Variants")
        constraints = [
            models.UniqueConstraint(fields=["product", "variant_type", "value"], name="unique_variant_per_product"),
        ]
        
class CustomizationOption(models.Model):
    class GroupTitleChoices(models.TextChoices):
        SingleSelect   = 'single'  , _('Single Select')
        MultiSelect    = 'multi'   , _('Multi Select')
        Text           = 'text'    , _('Text')
        Number         = 'number'  , _('Number')
        ImageUpload    = 'image'   , _('Image Upload')

    product   = models.ForeignKey(Product,on_delete=models.CASCADE,related_name="options",verbose_name=_("Product"))
    group_title = models.CharField(max_length=100,verbose_name=_("Group Title"))
    option_type	= models.CharField(max_length=10,choices=GroupTitleChoices,default=GroupTitleChoices.SingleSelect,verbose_name=_("Option Type"))
    is_required	= models.BooleanField(default=False,verbose_name=_("Is Required"))
    min_select	= models.PositiveSmallIntegerField(default=0,verbose_name=_("Min Select"))
    max_select	= models.PositiveSmallIntegerField(default=0,verbose_name=_("Max Select"))
    # values

    def __str__(self):
        return f'{self.product}  - {self.group_title}' # type: ignore
    
    def clean(self):
        super().clean()
        if self.max_select and self.min_select > self.max_select:
            raise ValidationError(_("min_select cannot be greater than max_select."))
        if self.option_type in (self.GroupTitleChoices.Text, self.GroupTitleChoices.Number, self.GroupTitleChoices.ImageUpload):
            if self.max_select not in (0, 1) or self.min_select not in (0, 1):
                raise ValidationError(_("For text/number/image options min/max must be 0 or 1."))

    class Meta:
        db_table = "customization_option"
        verbose_name = _("Customization Option")
        verbose_name_plural = _("Customization Options")
        constraints = [
            models.UniqueConstraint(fields=["product", "group_title"], name="unique_option_per_product"),
        ]

class CustomizationValue(models.Model):
    option  = models.ForeignKey(CustomizationOption,on_delete=models.CASCADE,related_name="values",verbose_name=_("Option"))
    title   = models.CharField(max_length=100,verbose_name=_("Title"))
    image   = models.ImageField(upload_to=upload_to_name,validators=[validate_image],blank=True,null=True,verbose_name=_("Image"))
    extra_price= models.DecimalField(max_digits=10, decimal_places=0,default=0,verbose_name=_("Extra Price")) # type: ignore
    is_active  = models.BooleanField(default=True,verbose_name=_("Is Active"))
    # is_default = models.BooleanField(default=False,verbose_name=_("Is Default"))

    def clean(self):
        super().clean()
        if not (self.title or "").strip():
            raise ValidationError({"title": _("Title cannot be empty.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.option} - {self.title}' # type: ignore

    class Meta:
        db_table = "customization_value"
        verbose_name = _("Customization Value")
        verbose_name_plural = _("Customization Values")
        constraints = [
            models.UniqueConstraint(fields=["option", "title"], name="unique_value_per_option"),
        ]
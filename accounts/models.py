import uuid
from pathlib import Path

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from django_jalali.db import models as jmodels


def validate_avatar(file):
    max_size = 300 * 1024  # 300 KB
    valid_extensions = ["jpg", "jpeg", "png", "webp"]

    extension = Path(file.name).suffix.lower().replace(".", "")
    if extension not in valid_extensions:
        raise ValidationError( _("Valid formats are: JPG, JPEG, PNG and WEBP."))

    if file.size > max_size:
        raise ValidationError( _("File size must be less than 300 KB."))

def upload_to_avatar(instance, filename):
    extension = Path(filename).suffix.lower()
    username = instance.username or "user"
    new_filename = f"{username}_{uuid.uuid4().hex}{extension}"
    return f"profile/avatar/{new_filename}"

class CustomUser(AbstractUser):
    class GenderChoices(models.TextChoices):
        MALE = "m", _("Male")
        FEMALE = "f", _("Female")

    phone       = models.CharField(max_length=13, unique=True, null=True, blank=True,verbose_name=_("Phone Number"))
    phone_verified = models.BooleanField(default=False,verbose_name=_("Verified Phone Number"))
    email       = models.EmailField(unique=True, null=True, blank=True,verbose_name=_("Email Address"))
    birth_date  = jmodels.jDateField(null=True, blank=True,help_text=_("Enter the date of birth in the solar calendar. Exm: 1374-01-01"),verbose_name=_("Birth Date"))
    national_code = models.CharField(max_length=10, null=True, blank=True,validators=[ RegexValidator(regex=r"^[0-9]{10}$")],verbose_name=_("National Code"))
    gender      = models.CharField(max_length=1, choices=GenderChoices.choices, null=True, blank=True,verbose_name=_("Gender"))
    avatar      = models.ImageField(upload_to=upload_to_avatar, validators=[ validate_avatar], blank=True, null=True, verbose_name=_("Avatar"))
    loyalty_points = models.PositiveIntegerField(default=0,verbose_name=_("Loyalty Points"))
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=0, default=0,verbose_name=_("Wallet Balance")) # type: ignore

    def get_name(self):
        if self.first_name and self.last_name:
            return "%s %s" %(self.first_name,self.last_name)
        elif self.first_name:
            return self.first_name
        else:
            return "%s" %self.username
    
    def __str__(self):
        return self.username
    
    class Meta:
        db_table = "custom_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

class Address(models.Model):
    class ProvinceChoices(models.TextChoices):
        Ardabil = "01", _("Ardabil")

    class CityChoices(models.TextChoices):
        Ardabil = "01", _("Ardabil")

    
    user    = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="%(class)s",verbose_name=_("User"))
    title   = models.CharField(max_length=100,help_text=_("Enter a title for this address, e.g., Home, Office, etc."),verbose_name=_("Address Title"))
    receiver_name   = models.CharField(max_length=100,verbose_name=_("Receiver Name"))
    receiver_phone  = models.CharField(max_length=13,verbose_name=_("Receiver Phone Number"))
    province    = models.CharField(max_length=100, choices=ProvinceChoices.choices,default=ProvinceChoices.Ardabil,verbose_name=_("Province"))
    city        = models.CharField(max_length=100, choices=CityChoices.choices,default=CityChoices.Ardabil,verbose_name=_("City"))
    address     = models.TextField(max_length=300,help_text=_("Enter the full address including street, alley, etc."),verbose_name=_("Address"))
    postal_code = models.CharField(max_length=10,validators=[ RegexValidator(regex=r"^[0-9]{10}$")],verbose_name=_("Postal Code"))
    plaque_number = models.CharField(max_length=10,verbose_name=_("Plaque Number"))
    block       = models.PositiveSmallIntegerField(blank=True,null=True,verbose_name=_("Block"))
    floor       = models.PositiveSmallIntegerField(blank=True,null=True,verbose_name=_("Floor"))
    unit        = models.PositiveSmallIntegerField(blank=True,null=True,verbose_name=_("Unit"))
    is_default  = models.BooleanField(default=False,verbose_name=_("Default Address"))
    created_date= models.DateTimeField(auto_now_add=True,verbose_name=_("Created Date"))

    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    class Meta:
        db_table = "user_address"
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_is_default_per_user",
                )
            ]

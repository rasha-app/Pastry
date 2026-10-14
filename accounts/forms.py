import phonenumbers

from io import BytesIO
from pathlib import Path
from typing import Any
from PIL import Image

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.urls import reverse


from django_jalali import forms as jforms
from allauth.account.forms import LoginForm as BaseLoginForm

from accounts.models import CustomUser,Address

IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'webp'}

def compress_image_file(media,max_size_mb: float = 0.5,max_dimension: int = 1920,quality: int = 75,threshold_kb: int = 300,):
    """
    فشرده‌سازی یک فایل تصویری.
    - اگر فایل غیرتصویری باشد یا از قبل کوچک باشد، دست‌نخورده برگردانده می‌شود.
    - اگر خطایی رخ دهد یا خروجی بزرگ‌تر از ورودی شود، فایل اصلی برگردانده می‌شود.
    """
    if not media:
        return media

    ext = Path(media.name).suffix.lower().lstrip('.')
    if ext not in IMAGE_EXTS:
        return media  # mp3, mp4, pdf و... دست نزن

    if media.size <= threshold_kb * 1024:
        return media  # از قبل کوچک است

    try:
        media.seek(0)
        img = Image.open(media)

        # کوچک کردن ابعاد در صورت نیاز
        if max(img.size) > max_dimension:
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS  # type: ignore Pillow قدیمی
            img.thumbnail((max_dimension, max_dimension), resample)

        # برای JPEG باید RGB باشد، بقیه RGBA
        if img.mode in ('RGBA', 'P', 'LA'):
            if ext in ('jpg', 'jpeg'):
                img = img.convert('RGB')
            else:
                img = img.convert('RGBA')

        output = BytesIO()
        save_kwargs: dict[str, Any] = {'optimize': True}
        if ext in ('jpg', 'jpeg'):
            save_kwargs['quality'] = quality
            save_kwargs['format'] = 'JPEG'
        elif ext == 'png':
            save_kwargs['format'] = 'PNG'
        elif ext == 'webp':
            save_kwargs['quality'] = quality
            save_kwargs['format'] = 'WEBP'

        img.save(output, **save_kwargs)
        output.seek(0)
        new_size = output.getbuffer().nbytes

        # اگر فایل جدید بزرگ‌تر شد، همان اصلی را نگه دار
        if new_size >= media.size:
            media.seek(0)
            return media
        return InMemoryUploadedFile(output,field_name='image',name=media.name,content_type=f'image/{ext}',size=new_size,charset=None,)
    except Exception:
        # در صورت هر خطایی، فایل اصلی برگردانده می‌شود
        try:
            media.seek(0)
        except Exception:
            pass
        return media

class ProfileForms(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("username","first_name","last_name","gender","birth_date","avatar",)

        widgets = {
            "birth_date": jforms.jDateInput(attrs={"type": "text", "class": "form-control","placeholder": _("Exm: 1405-01-01 Solar calendar")}),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
        }
       
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 2. تغییر متن دکمه انتخاب فایل
        self.fields['avatar'].widget.input_text = _("No files selected")
        
        # 4. ساخت لینک مشاهده با آدرس کوتاه شده (در help_text)
        if self.instance and self.instance.avatar:
            url = self.instance.avatar.url
            short_url = url[:40] + '...' if len(url) > 50 else url

            # ایجاد لینک با direction ltr برای جلوگیری از بهم ریختگی
            self.fields['avatar'].help_text = mark_safe(
                f'<span dir="ltr" style="display: inline-block; word-break: break-all; max-width: 100%;">'
                f'<a href="{url}" target="_blank">{short_url}</a>'
                f'</span>'
            )
        else:
            self.fields['avatar'].help_text = _("No files selected")

    def clean_avatar(self):
        return compress_image_file(self.cleaned_data.get('avatar'),max_size_mb=0.5,max_dimension=1920,)

class AddressForms(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "title","receiver_name","receiver_phone","province","city","address",
            "postal_code","plaque_number","block","floor","unit","is_default",
            )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # اولین آدرس کاربر خودکار default می‌شود
        if not self.instance.pk and not self.instance.user_id:
            return
        if not self.instance.pk and not Address.objects.filter(user=self.instance.user).exists():
            self.fields['is_default'].initial = True


# Login By Phone
class LoginPhoneForm(forms.Form):
    phone = forms.CharField(
        label=_("Phone Number"),
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": _("Exm: 09123456789"), "dir": "ltr"}),
    )

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        try:
            parsed = phonenumbers.parse(phone, "IR")
            if not phonenumbers.is_valid_number(parsed):
                raise ValidationError(_("Invalid phone number."))
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            raise ValidationError(_("Invalid phone number format."))

class LoginCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={"placeholder": _("6 Digit Code")}),
        label=_("Verified Code")
    )

# Reset By Phone
class ResetPhoneForm(forms.Form):
    phone = forms.CharField(
        label=_("Phone Number"),
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": _("Exm: 09123456789"), "dir": "ltr"}),
    )

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        try:
            parsed = phonenumbers.parse(phone, "IR")
            if not phonenumbers.is_valid_number(parsed):
                raise ValidationError(_("Invalid phone number."))
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            raise ValidationError(_("Invalid phone number format."))

class ResetCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={"placeholder": _("6 Digit Code")}),
        label=_("Verified Code")
    )

class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(label=_("New Password"),widget=forms.PasswordInput,min_length=8,)
    password2 = forms.CharField(label=_("Confirm New Password"),widget=forms.PasswordInput,min_length=8,)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError(_("Passwords do not match."))
        return cleaned


# Show Reset Password And Login By Phone In Allauth Login Template
class CustomLoginForm(BaseLoginForm):
    """
    افزودن لینک «فراموشی رمز» و «ورود با شماره» زیر فیلد رمز عبور.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        reset_url = reverse("reset_password_phone")
        phone_url = reverse("login_by_phone")

        self.fields['password'].help_text = format_html(
            '<a class="auth-help-link" href="{}">{}</a>'
            '<br>'
            '<a class="auth-help-link" href="{}">{}</a>',
            reset_url, _("Forgot your password?"),
            phone_url, _("Login with Phone"),
        )
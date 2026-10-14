import phonenumbers, logging

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache

from allauth.account.adapter import DefaultAccountAdapter


User = get_user_model()
logger = logging.getLogger(__name__)
PHONE_VERIFY_CODE_TTL = getattr(settings,"PHONE_VERIFY_CODE_TTL",120)

def send_sms_ir(phone,code):
    import json,http.client

    conn = http.client.HTTPSConnection("api.sms.ir")
    payload_dict = {
        "mobile": phone,
        "templateId": getattr(settings,'SMS_IR_TEMPLATE_ID'),
        "parameters": [{"name": "CODE","value": str(code)}]
    }

    payload = json.dumps(payload_dict)
    headers = {'Content-Type': 'application/json','Accept': 'text/plain','x-api-key': getattr(settings,'SMS_IR_API_KEY')}

    try:
        conn.request("POST", "/v1/send/verify", payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        response_json = json.loads(data)
        if settings.DEBUG:
            print(response_json)
        return response_json
    except Exception as e:
        logger.exception(msg=f'An unexpected error occurred in function <send_sms_ir>: {e}')
        return {'status':9}
    finally:
        conn.close()



# ========== کلاس فیلد سفارشی برای شماره موبایل ==========
class IranianPhoneField(forms.CharField):
    """
    فیلد فرم سفارشی که شماره موبایل را با phonenumbers اعتبارسنجی
    و به فرمت E.164 نرمال‌سازی می‌کند.
    """
    def clean(self, value):
        value = super().clean(value)
        if not value:
            return value

        try:
            parsed = phonenumbers.parse(value, "IR")
            if not phonenumbers.is_valid_number(parsed):
                raise ValidationError(_("Mobile number is invalid."))

            normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

            # ✅ بررسی یکتایی
            if User.objects.filter(phone=normalized).exists():
                raise ValidationError(_("This mobile number is already registered."))

            return normalized
        except phonenumbers.NumberParseException:
            raise ValidationError(_("The mobile number format is invalid."))


# ========== آداپتور سفارشی ==========
class MyAccountAdapter(DefaultAccountAdapter):

    # ========== ذخیره و خواندن شماره ==========
    def set_phone(self, user, phone, verified=False):
        logger.info(f"set_phone called: user={user.username}, phone={phone}, verified={verified}")  # type: ignore
        user.phone = phone # type: ignore
        user.phone_verified = verified # type: ignore
        if user.pk:
            user.save(update_fields=['phone', 'phone_verified'])
        else:
            user.save()

    def get_phone(self, user):
        if user.phone:  # type: ignore
            return (user.phone, user.phone_verified)  # type: ignore
        return None

    def set_phone_verified(self, user, phone):
        logger.info(f"set_phone_verified: {user.username} -> {phone}") # type: ignore
        user.phone = phone  # type: ignore
        user.phone_verified = True  # type: ignore
        user.save(update_fields=['phone', 'phone_verified'])
                  
    def get_user_by_phone(self, phone):
        return User.objects.filter(phone=phone).first()

    # ========== ارسال پیامک ==========
    def send_verification_code_sms(self, user, phone, code, **kwargs):
        cache.set(f'phone_send_cache_code{phone}', code, timeout=PHONE_VERIFY_CODE_TTL)
        send_sms_ir(phone,code)
        # send_ghasedak_sms(phone,code)
        if settings.DEBUG:
            print(f"[SMS] به {phone} ارسال شد: کد {code}")

    def send_unknown_account_sms(self, phone, **kwargs):
        """
        به شماره ناشناس پیامک نمی‌فرستیم.
        فقط لاگ می‌کنیم تا از سوءاستفاده و هزینه اضافی جلوگیری شود.
        """
        if settings.DEBUG:
            print(f"[SMS] شماره ناشناس: {phone} - پیامکی ارسال نشد.")
        # یا اگر logger دارید:
        logger.info(f"Unknown phone attempted: {phone}")

    # ========== فیلد فرم سفارشی (مهم‌ترین بخش) ==========
    def phone_form_field(self, **kwargs):
        """
        برگرداندن فیلد فرم سفارشی که اعتبارسنجی را انجام می‌دهد.
        """
        return IranianPhoneField(
            label=kwargs.get("label", "شماره موبایل"),
            required=kwargs.get("required", True),
            widget=forms.TextInput(attrs={
                "type": "tel",
                "placeholder": "09123456789",
                "dir": "ltr",
            }),
        )

    
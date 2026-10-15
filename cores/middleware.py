# core/middleware.py
from django.conf import settings
from django.utils import translation

class ForceDefaultLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # اگر کاربر کوکی زبان ندارد، یعنی اولین بار است که وارد سایت می‌شود
        if not request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME):
            # هدر مرورگر را به‌زور فارسی می‌کنیم
            request.META['HTTP_ACCEPT_LANGUAGE'] = settings.LANGUAGE_CODE
            # زبان را برای این درخواست فعال می‌کنیم
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = settings.LANGUAGE_CODE

        response = self.get_response(request)

        # اگر کوکی نبود، یک کوکی با عمر طولانی برای فارسی تنظیم می‌کنیم
        if not request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME):
            if not response.cookies.get(settings.LANGUAGE_COOKIE_NAME):
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME,
                    settings.LANGUAGE_CODE,
                    max_age=settings.LANGUAGE_COOKIE_AGE,
                )

        return response
import time, secrets,logging

from django.db import transaction
from django.shortcuts import get_object_or_404, render,redirect
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from .models import Address
from .forms import (
        ResetCodeForm, ResetPhoneForm,ResetPasswordForm,
        ProfileForms,AddressForms,
        LoginPhoneForm,LoginCodeForm
    )
from .utils import clear_otp, get_cached_otp, send_otp_to_phone

User = get_user_model()
CACHE_TIME = getattr(settings,"PHONE_VERIFY_CODE_TTL",120)
PREFIX_RESET_PASS = 'reset_pass_'
PREFIX_LOGIN_OTP = 'login_otp_'
logger = logging.getLogger(__name__)

# ------------------- Template View -------------------------- #
class LoginInPhoneView(TemplateView):
    template_name = 'login_by_phone.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.request.session
        phone = session.get(f'{PREFIX_LOGIN_OTP}phone', '')
        show_code_form = session.get(f'{PREFIX_LOGIN_OTP}show_code_form', False)

        context['form'] = LoginPhoneForm()
        context['verified_form'] = LoginCodeForm()
        context['show_verified'] = show_code_form
        if show_code_form:
            context['phone_display'] = phone
        return context

    def post(self, request, *args, **kwargs):
        session = request.session

        # ========== مرحله ۱: ارسال کد ==========
        if 'code_send' in request.POST:
            form = LoginPhoneForm(request.POST)
            if not form.is_valid():
                for error in form.errors.values():
                    messages.warning(request, error) # type: ignore
                return redirect('login_by_phone')

            phone = form.cleaned_data['phone']  # E.164

            if not User.objects.filter(phone=phone, phone_verified=True).exists():
                # پیام امنیتی کلی
                messages.warning(request, _('If this phone is registered, a code will be sent.'))
                return self._reset_session(request, to='login_by_phone')

            rate_key = f'login_otp_{phone}_rate'
            if cache.get(rate_key):
                messages.warning(request, _('Please wait 60 seconds before requesting a new code.'))
                return redirect('login_by_phone')

            res = send_otp_to_phone(phone, suffix='_login_otp')
            if res['status'] == 1:
                messages.info(request, res['msg'])
                session.update({
                    f'{PREFIX_LOGIN_OTP}phone': phone,
                    f'{PREFIX_LOGIN_OTP}show_code_form': True,
                })
                cache.set(rate_key, True, 60)
            else:
                messages.warning(request, res['msg'])
            return redirect('login_by_phone')

        # ========== مرحله ۲: تأیید کد ==========
        if 'login_otp' in request.POST:
            phone = session.get(f'{PREFIX_LOGIN_OTP}phone')
            if not phone:
                messages.error(request, _('Session expired, try again.'))
                return self._reset_session(request, to='login_by_phone')

            form = LoginCodeForm(request.POST)
            if not form.is_valid():
                messages.error(request, _('Invalid OTP code.'))
                return redirect('login_by_phone')

            user_code = form.cleaned_data['code']
            otp_data = get_cached_otp(phone, suffix='_login_otp')
            if not otp_data:
                messages.error(request, _('OTP expired'))
                return self._reset_session(request, to='login_by_phone')

            remaining = int(otp_data['expire'] - time.time())
            if remaining <= 0 or otp_data['attempts'] >= 3:
                messages.error(request, _('OTP expired'))
                clear_otp(phone, suffix='_login_otp')
                return self._reset_session(request, to='login_by_phone')

            if str(user_code) == str(otp_data['code']):
                # ✅ تأیید موفق: لاگین نکن! فقط یک نشانه در سشن بگذار
                clear_otp(phone, suffix='_login_otp')
                user = get_object_or_404(User,phone=phone,phone_verified=True)
                login(request,user=user,backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, _('Login Successfully.'))
                return redirect('/')  # URL جدید

            # کد اشتباه
            otp_data['attempts'] += 1
            cache.set(f'{phone}_login_otp', otp_data, remaining)
            messages.warning(
                request,
                _('Wrong code. Remaining attempts: {remain}').format(remain=3 - otp_data['attempts'])
            )
            return redirect('login_by_phone')

        return redirect('login_by_phone')

    def _reset_session(self, request, to='login_by_phone'):
        session = request.session
        for key in [
            f'{PREFIX_LOGIN_OTP}phone',
            f'{PREFIX_LOGIN_OTP}show_code_form',
        ]:
            session.pop(key, None)
        return redirect(to)

class ResetPassInPhoneView(TemplateView):
    template_name = 'reset_pass_by_phone.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.request.session
        phone = session.get(f'{PREFIX_RESET_PASS}phone', '')
        expire = session.get(f'{PREFIX_RESET_PASS}expire', 0)
        show_code_form = session.get(f'{PREFIX_RESET_PASS}show_code_form', False)

        context['form'] = ResetPhoneForm()
        context['verified_form'] = ResetCodeForm()
        context['show_verified'] = show_code_form
        context['expire_time'] = expire
        if show_code_form:
            context['phone_display'] = phone
        return context

    def post(self, request, *args, **kwargs):
        session = request.session

        # ========== مرحله ۱: ارسال کد ==========
        if 'code_send' in request.POST:
            form = ResetPhoneForm(request.POST)
            if not form.is_valid():
                for error in form.errors.values():
                    messages.warning(request, error) # type: ignore
                return redirect('reset_password_phone')

            phone = form.cleaned_data['phone']  # E.164

            if not User.objects.filter(phone=phone, phone_verified=True).exists():
                # پیام امنیتی کلی
                messages.warning(request, _('If this phone is registered, a code will be sent.'))
                return self._reset_session(request, to='reset_password_phone')

            rate_key = f'reset_pass_{phone}_rate'
            if cache.get(rate_key):
                messages.warning(request, _('Please wait 60 seconds before requesting a new code.'))
                return redirect('reset_password_phone')

            res = send_otp_to_phone(phone, suffix='_reset_pass')
            if res['status'] == 1:
                messages.info(request, res['msg'])
                session.update({
                    f'{PREFIX_RESET_PASS}phone': phone,
                    f'{PREFIX_RESET_PASS}show_code_form': True,
                    f'{PREFIX_RESET_PASS}expire': CACHE_TIME,
                })
                cache.set(rate_key, True, 60)
            else:
                messages.warning(request, res['msg'])
            return redirect('reset_password_phone')

        # ========== مرحله ۲: تأیید کد ==========
        if 'reset_pass' in request.POST:
            phone = session.get(f'{PREFIX_RESET_PASS}phone')
            if not phone:
                messages.error(request, _('Session expired, try again.'))
                return self._reset_session(request, to='reset_password_phone')

            form = ResetCodeForm(request.POST)
            if not form.is_valid():
                messages.error(request, _('Invalid OTP code.'))
                return redirect('reset_password_phone')

            user_code = form.cleaned_data['code']
            otp_data = get_cached_otp(phone, suffix='_reset_pass')
            if not otp_data:
                messages.error(request, _('OTP expired'))
                return self._reset_session(request, to='reset_password_phone')

            remaining = int(otp_data['expire'] - time.time())
            if remaining <= 0 or otp_data['attempts'] >= 3:
                messages.error(request, _('OTP expired'))
                clear_otp(phone, suffix='_reset_pass')
                return self._reset_session(request, to='reset_password_phone')

            if str(user_code) == str(otp_data['code']):
                # ✅ تأیید موفق: لاگین نکن! فقط یک نشانه در سشن بگذار
                clear_otp(phone, suffix='_reset_pass')
                session[f'{PREFIX_RESET_PASS}verified_phone'] = phone
                session[f'{PREFIX_RESET_PASS}token'] = secrets.token_urlsafe(32)
                messages.success(request, _('Phone verified. Please set your new password.'))
                return redirect('reset_password_set')  # URL جدید

            # کد اشتباه
            otp_data['attempts'] += 1
            cache.set(f'{phone}_reset_pass', otp_data, remaining)
            messages.warning(
                request,
                _('Wrong code. Remaining attempts: {remain}').format(remain=3 - otp_data['attempts'])
            )
            session[f'{PREFIX_RESET_PASS}expire'] = remaining
            return redirect('reset_password_phone')

        return redirect('reset_password_phone')

    def _reset_session(self, request, to='reset_password_phone'):
        session = request.session
        for key in [
            f'{PREFIX_RESET_PASS}phone',
            f'{PREFIX_RESET_PASS}show_code_form',
            f'{PREFIX_RESET_PASS}expire',
            f'{PREFIX_RESET_PASS}verified_phone',
            f'{PREFIX_RESET_PASS}token',
        ]:
            session.pop(key, None)
        return redirect(to)

class ResetPasswordSetView(TemplateView):
    template_name = 'reset_password_set_by_phone.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ResetPasswordForm()
        return context

    def post(self, request, *args, **kwargs):
        session = request.session
        phone = session.get(f'{PREFIX_RESET_PASS}verified_phone')
        token = session.get(f'{PREFIX_RESET_PASS}token')
        if not phone or not token:
            messages.error(request, _('Session expired. Please start over.'))
            return redirect('reset_password_phone')

        form = ResetPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user = User.objects.filter(phone=phone, phone_verified=True).first()
        if not user:
            messages.error(request, _('User not found.'))
            return redirect('reset_password_phone')

        user.set_password(form.cleaned_data['password1'])
        user.save()

        for key in [f'{PREFIX_RESET_PASS}verified_phone', f'{PREFIX_RESET_PASS}token']:
            session.pop(key, None)

        messages.success(request, _('Password reset successfully. Please login.'))
        return redirect('account_login')  # یا صفحه لاگین خودت
    
class ProfileViews(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'

    # Context
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # only bind the form that failed (passed via kwargs);
        # the other one renders fresh from the instance
        context['forms']=ProfileForms(instance=user, prefix='profile')
        context['address_forms']=AddressForms(instance=Address(user=user), prefix='address')

        context['addresses'] = Address.objects.filter(user=user).order_by('-is_default', '-created_date')
        return context

    # POST
    def post(self, request, *args, **kwargs):
        user = request.user
        print(request.POST)
        if 'profile_submit' in request.POST:
            return self._handle_profile(request, user)

        if 'address_submit' in request.POST:
            return self._handle_address_add(request, user)

        if 'address_delete' in request.POST:
            return self._handle_address_delete(request, user)

        logger.warning("Profile POST from user=%s with no recognized action", user.pk)
        return redirect('profile')

    # Handlers
    def _handle_profile(self, request, user):
        form = ProfileForms(request.POST, request.FILES,instance=user, prefix='profile',)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated successfully.'))
            logger.info("Profile updated for user=%s", user.pk)
            return redirect('profile')

        logger.warning("Profile form invalid for user=%s errors=%s",user.pk, form.errors.as_json(),)
        messages.warning(request, _(('Please fix the errors below and try again.')))
        return self.render_to_response(self.get_context_data(forms=form))

    def _handle_address_add(self, request, user):
        form = AddressForms(
            request.POST,
            instance=Address(user=user),
            prefix='address',
        )
        if form.is_valid():
            with transaction.atomic():
                address = form.save(commit=False)
                address.user = user

                # enforce single-default per user
                if address.is_default:
                    Address.objects.filter(user=user, is_default=True,).update(is_default=False)

                address.save()

            messages.success(request, _('Address added successfully.'))
            logger.info("Address created id=%s for user=%s", address.pk, user.pk)
            return redirect('profile')

        logger.warning(
            "Address form invalid for user=%s errors=%s",
            user.pk, form.errors.as_json(),
        )
        messages.warning(request, _('Please fix the errors below and try again.'))
        return self.render_to_response(self.get_context_data(address_forms=form))

    def _handle_address_delete(self, request, user):
        address_id = request.POST.get('address_id')
        try:
            address = Address.objects.get(pk=address_id, user=user)
        except Address.DoesNotExist:
            logger.warning(
                "User=%s tried to delete missing/foreign address id=%s",
                user.pk, address_id,
            )
            messages.error(request, _('Address not found.'))
            return redirect('profile')

        with transaction.atomic():
            was_default = address.is_default
            address.delete()

            # promote the most recent remaining address if we removed the default
            if was_default:
                fallback = (
                    Address.objects
                    .filter(user=user)
                    .order_by('-created_date')
                    .first()
                )
                if fallback:
                    fallback.is_default = True
                    fallback.save(update_fields=['is_default'])

        messages.success(request, _('Address removed successfully.'))
        logger.info("Address id=%s deleted for user=%s", address_id, user.pk)
        return redirect('profile')
    

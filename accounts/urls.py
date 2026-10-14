from django.urls import path

from .views import LoginInPhoneView, ProfileViews, ResetPassInPhoneView, ResetPasswordSetView

urlpatterns = [
    path('login-by-phone/',LoginInPhoneView.as_view(),name='login_by_phone'),
    path('reset-password-phone/',ResetPassInPhoneView.as_view(),name='reset_password_phone'),
    path('reset-password-set/', ResetPasswordSetView.as_view(), name='reset_password_set'),
    path('profile/',ProfileViews.as_view(),name='profile'),
]


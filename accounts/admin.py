from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from import_export import resources
from import_export.admin import ImportExportModelAdmin

from unfold.admin import ModelAdmin
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import Address

User = get_user_model()


class CustomUserResourece(resources.ModelResource):
    class Meta:
        model = User
    def before_save_instance(self, instance, using_transactions, dry_run):
        # این کد باعث می‌شود پسورد هنگام ایمپورت هش شود
        if instance.password:
            instance.set_password(instance.password)

class AddressInline(admin.StackedInline):
    model = Address
    extra = 0

@admin.register(Address)
class AddressAdmin(ImportExportModelAdmin,ModelAdmin):
    list_display = ['id','user','title','receiver_name','receiver_phone']
    list_display_links = ['id','user']
    search_fields = ('user__username',)
    list_per_page = 20
    save_on_top = True

@admin.register(User)
class CustomUserAdmin(ImportExportModelAdmin,ModelAdmin,UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    resource_class = CustomUserResourece
    model = User # type: ignore
    fieldsets = (
        (_('Login information'), {
            'fields': ('username','password',)
        }),

        (_('Personal information'), {
            'fields': ('first_name','last_name','email','phone','phone_verified','gender','birth_date','national_code','loyalty_points','wallet_balance')
        }),

        (_('Profile images'), {
            'fields': ('avatar',)
        }),

        (_('Permissions'), {
            'fields': ('is_active','is_staff','is_superuser','groups','user_permissions',
            )
        }),

        (_('Important dates'), {
            'fields': ('last_login','date_joined',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),'fields': ('username','email','phone','password1','password2',),
        }),
    )
    list_display = ('id','get_name','phone','gender','phone_verified','is_active','is_staff',)
    list_display_links = ('id','get_name',)
    list_filter = ('is_active','is_staff','is_superuser','gender',)
    search_fields = ('get_name','email','phone',)
    ordering = ('id',)
    list_editable = ['gender','phone_verified','is_active','is_staff',]
    list_per_page = 20
    inlines = (AddressInline,)
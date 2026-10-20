from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter(name='per_num')
def english_number_to_persian(value):
    value = str(value)
    en_to_per = value.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹')
    return value.translate(en_to_per)

@register.filter
def get_class_name(obj):
    return obj.__class__.__name__

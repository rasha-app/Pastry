
from django import forms
from django.utils.translation import gettext_lazy as _


from .models import Contact


class ContactForm(forms.ModelForm):
    # Honeypot فیلد مخفی برای جلوگیری از اسپم
    honeypot = forms.CharField(required=False,widget=forms.HiddenInput(),label='')

    class Meta:
        model = Contact
        fields = ['user_name', 'email', 'phone','subject', 'message']
        labels = {
            'user_name': _('Name and Last Name'),
        }
        widgets = {
            'user_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Your name')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Your email')
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Exam: 09010001111')
            }),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Write your message...'),
                'rows': 5
            })
        }
    
    def clean_honeypot(self):
        """بررسی Honeypot - اگر ربات باشه این فیلد رو پر میکنه"""
        honeypot = self.cleaned_data.get('honeypot')
        if honeypot:
            raise forms.ValidationError(_('Bot detected.'))
        return honeypot
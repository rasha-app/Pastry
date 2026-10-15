from pathlib import Path
import uuid
from PIL import Image

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone 
from django.utils.text import slugify

import jdatetime

def default_working_hours():
        return {
            "saturday": "08:00-20:00",
            "sunday": "08:00-20:00",
            "monday": "08:00-20:00",
            "tuesday": "08:00-20:00",
            "wednesday": "08:00-20:00",
            "thursday": "08:00-17:00",
            "friday": "closed",
        }

def validate_file_extension(file):
    max_img_size = 1000  * 1024  # 1 MB
    max_mp4_size = 60000 * 1024  # 60 MB
    max_mp3_size = 6000  * 1024  # 6 MB

    valid_extensions = ['jpg', 'jpeg', 'png', 'webp','mp3','mp4']

    extension = Path(file.name).suffix.lower().replace('.', '')

    if extension not in valid_extensions:
        raise ValidationError(
            _('Valid formats are: JPG, JPEG, PNG , MP3 , MP4 and WEBP.')
        )

    if extension == 'mp4':
        if file.size > max_mp4_size:
            raise ValidationError(_('File size must be less than 60 MB.'))
        
    elif extension == 'mp3':
        if file.size > max_mp3_size:
            raise ValidationError(_('File size must be less than 6 MB.'))
        
    elif extension in ['jpg', 'jpeg', 'png', 'webp']:
        if file.size > max_img_size:
            raise ValidationError(_('File size must be less than 1 MB.'))
        try:
            img = Image.open(file)
            img.verify()
            file.seek(0)  # ریست اشاره‌گر برای ذخیره‌سازی
            # چک ابعاد برای جلوگیری از Decompression Bomb
            img = Image.open(file)
            if img.width * img.height > 25_000_000:  # مثلاً 25 مگاپیکسل
                raise ValidationError(_('Image dimensions are too large.'))
            file.seek(0)
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(_('The submitted file is not a valid image.'))
    else:
        raise ValidationError(_('Unspecified error'))

def uploader_check_name(instance, filename):
    model_name = instance.__class__.__name__.lower()
    extension = Path(filename).suffix.lower()

    new_filename = slugify(Path(filename).stem)
    if not new_filename:
        new_filename = uuid.uuid4().hex

    dt = timezone.now().date()
    jalali = jdatetime.date.fromgregorian(date=dt)

    ext = extension.lower().replace('.', '')
    return f'{model_name}/media/{ext}/{jalali.year}-{jalali.month}-{jalali.day}/{new_filename}{extension}'

class Contact(models.Model):
    class SubjectChoices(models.TextChoices):
        SUGGESTION  = '1' , _('suggestion')
        REPORT      = '2' , _('report')
        ADVERTISING = '3' , _('advertising')
        SUPPORT     = '4' , _('support')
        OTHER       = '5' , _('other')

    user_name = models.CharField(max_length=150,verbose_name=_('User Name'))
    email     = models.EmailField(verbose_name=_('Email'))
    phone     = models.CharField(max_length=13,verbose_name=_('Phone'))
    subject   = models.CharField(max_length=2, choices=SubjectChoices.choices, default=SubjectChoices.SUPPORT,verbose_name=_('Subject'))
    message   = models.TextField(max_length=600,verbose_name=_('Message'))
    created_date= models.DateTimeField(auto_now_add=True,verbose_name=_('Created Date'))

    def __str__(self):
        return f"{self.user_name} -> {self.get_subject_display()} -> {self.message[:30]}" # type: ignore
    
    class Meta:
        db_table = 'contact'
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')

class SiteInfo(models.Model):
    email       = models.EmailField(max_length=50,verbose_name=_('Email'),default='example@gmail.com')
    phone       = models.CharField(max_length=20,verbose_name=_('Phone'),default='+98 914 000 0000')
    telegram    = models.URLField(max_length=50,verbose_name=_('Telegram'),default='https://telegram.org')
    instagram   = models.URLField(max_length=50,verbose_name=_('Instagram'),default='https://instagram.com')
    facebook    = models.URLField(max_length=50,verbose_name=_('Facebook'),default='https://facebook.com')
    twitter      = models.URLField(max_length=50,verbose_name=_('Twitter'),default='https://x.com')
    whatsapp    = models.URLField(max_length=50,verbose_name=_('Whatsapp'),default='https://whatsapp.com')
    address_url = models.URLField (max_length=250,verbose_name=_('Address Url'),default='https://maps.app.goo.gl/9S6wDcm5yVqi6pZJ8')
    address     = models.CharField(max_length=300,verbose_name=_('Address'),default='Ardabil, Shariati Square, next to the Central Bank, Baklava Bakery')
    working_hours   = models.JSONField(verbose_name=_('working hours'),default=default_working_hours)

    def __str__(self):
            return f"{self.email} - {self.phone} - {self.address}" # type: ignore
    
    class Meta:
        db_table = 'site_info'
        verbose_name = _('Site Info')
        verbose_name_plural = _('Site Info')

class About(models.Model):
    title = models.CharField(max_length=150,blank=True,null=True,verbose_name=_('Title'),default='شیرینی پزی باقلوا')
    description  = models.TextField(max_length=300,blank=True,null=True,verbose_name=_('Description'),
                            default='این فروشگاه شیرینی‌پزی با بیش از ۲۰ سال سابقه، در زمینه پخت انواع شیرینی خشک و تر فعالیت می‌کند و شیرینی باقلوا از محصولات معروف آن است.')
    text  = models.TextField(max_length=2000,blank=True,null=True,verbose_name=_('Text'),
                            default='این مجموعه با هدف ارائه شیرینی‌های باکیفیت و خوش‌طعم فعالیت خود را آغاز کرده و طی سال‌ها توانسته اعتماد مشتریان زیادی را جلب کند. تخصص اصلی ما پخت انواع شیرینی خشک و تر است و شیرینی باقلوا یکی از شناخته‌شده‌ترین و محبوب‌ترین محصولات ماست.')
    poster_image = models.FileField(upload_to=uploader_check_name,validators=[validate_file_extension],blank=True,null=True,verbose_name=_('Poster Image'))
    created_date= models.DateTimeField(auto_now_add=True,verbose_name=_('Created Date'))
    # aboutimage
    def __str__(self):
                return f"{self.title} - {self.text[:20]} " # type: ignore
    class Meta:
        db_table = 'about'
        verbose_name = _('About')
        verbose_name_plural = _('About')
        
class AboutImage(models.Model):
    about = models.ForeignKey("cores.About",on_delete=models.CASCADE,related_name='%(class)s',verbose_name=_('About'))
    image = models.FileField(upload_to=uploader_check_name,validators=[validate_file_extension],verbose_name=_('Image'))
    title = models.CharField(max_length=200,verbose_name=_('Title'))

    def __str__(self):
        return f"{self.title} " # type: ignore
    class Meta:
        db_table = 'about_image'
        verbose_name = _('About Image')
        verbose_name_plural = _('About Images')
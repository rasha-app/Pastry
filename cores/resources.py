from import_export import resources
from .models import Contact, SiteInfo, About, AboutImage


class ContactResource(resources.ModelResource):
    class Meta:
        model = Contact


class SiteInfoResource(resources.ModelResource):
    class Meta:
        model = SiteInfo


class AboutResource(resources.ModelResource):
    class Meta:
        model = About


class AboutImageResource(resources.ModelResource):
    class Meta:
        model = AboutImage

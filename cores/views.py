from django.core.paginator import Paginator
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .forms import ContactForm
from .models import About, AboutImage, Contact


class HomeViews(TemplateView):
    template_name = 'home.html'

class ContactView(CreateView):
    model = Contact
    form_class = ContactForm
    template_name = 'contact.html'
    success_url = reverse_lazy('contact')

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            initial.update({
                'user_name': self.request.user.username,
                'email': getattr(self.request.user, 'email', ''),
                'phone': getattr(self.request.user, 'phone', ''),
                'subject': 'support',
            })
        return initial

    def form_valid(self, form):
        contact = form.save(commit=False)
        if self.request.user.is_authenticated:
            contact.user_name = self.request.user.username
            contact.email = self.request.user.email or 'example@gmail.com' # type: ignore
            contact.phone = getattr(self.request.user, 'phone', None) or '09010000000'
        
        messages.success(self.request,_('Submitted successfully'))
        return super().form_valid(form)
    

class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # مدل About در عمل singleton است. اگر ادمین اشتباهاً رکورد دوم
        # بسازد، جدیدترین رکورد نمایش داده می‌شود تا از سردرگمی جلوگیری شود.
        about = About.objects.order_by('-created_date').first()
        context['about'] = about
        # reverse accessor از related_name='%(class)s' → aboutimage
        if about is not None:
            context['about_images'] = about.aboutimage.all() # type: ignore
        else:
            context['about_images'] = AboutImage.objects.none()

        return context

def search(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        
        results = []
        
        # صفحه‌بندی نتایج
        paginator = Paginator(results, 10)  # نمایش 10 نتیجه در هر صفحه
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,  # نتایج صفحه‌بندی شده
            'query': query,
        }
        return render(request, 'search_results.html', context)

    # اگر فرم معتبر نبود یا جستجویی انجام نشده بود
    return render(request, 'search_results.html', {'query': query})

from django.urls import path

from .views import HomeViews,ContactView,AboutView,search


urlpatterns = [
    path(''         ,HomeViews.as_view()  ,name='home'),    
    path('contact/' ,ContactView.as_view(),name='contact'),    
    path('about/'   ,AboutView.as_view()  ,name='about'),    
    path('search/'  ,search ,name='search'),    
]

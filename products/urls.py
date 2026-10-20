from django.urls import path

from products.views import CategoryDetailView, ProductsListView, TagDetailView, ProductDetailView
from products.views import ProductCreateView, ProductUpdateView, ProductDeleteView
from products.views import TagAutocomplete, IngredientAutocomplete


urlpatterns = [
    path('tag/<int:pk>/',TagDetailView.as_view(),name='tag'),
    path('category/<int:pk>/',CategoryDetailView.as_view(),name='category'),
    
    path('',ProductsListView.as_view(),name='products_list'),

    path('create/',ProductCreateView.as_view(),name='product_create'),
    path('tag-autocomplete/',TagAutocomplete.as_view(),name='tag_autocomplete'),
    path('ingredient-autocomplete/',IngredientAutocomplete.as_view(),name='ingredient_autocomplete'),
    path('<int:pk>/<str:slug>/edit/',ProductUpdateView.as_view(),name='product_update'),
    path('<int:pk>/<str:slug>/delete/',ProductDeleteView.as_view(),name='product_delete'),

    path('<int:pk>/<str:slug>/',ProductDetailView.as_view(),name='product_detail'),

]


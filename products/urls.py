from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('create/', views.create_product, name='create_product'),
    path('update/<int:product_id>/', views.update_product, name='update_product'),
    path('edit-api/<int:api_product_id>/', views.edit_api_product, name='edit_api_product'),
    path('delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('api-delete/<int:product_id>/', views.api_delete_product, name='api_delete_product'),
]
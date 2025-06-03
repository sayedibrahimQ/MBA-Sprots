from django.urls import path
from . import views
app_name = 'ecommerce'


urlpatterns = [
    path('', views.products, name='products'),
    # path('order-confirmation/<int:order_id>/', views.order_confirmation_single_product, name='order_confirmation'),

]
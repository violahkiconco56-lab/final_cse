"""
URL configuration for hardware_sys project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from nyondo_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    #dashboard view
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('stock_dashboard/', views.stock_dashboard, name='stock_dashboard'),
    path('sales_dashboard/', views.sales_dashboard, name='sales_dashboard'),

    # stock management
    path("stock/", views.stock_list, name="stock_list"),
    path("stock/add/", views.add_stock, name="add_stock"),
    path("stock/edit/<int:stock_id>/", views.edit_stock, name="edit_stock"),
    path("stock/delete/<int:stock_id>/", views.delete_stock, name="delete_stock"),
    

    
]

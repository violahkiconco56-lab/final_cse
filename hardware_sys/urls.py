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

    # sales management
    path("sales/", views.sales_list, name="sales_list"),
    path("sales/add/", views.add_sale, name="add_sale"),
    path("sales/edit/<int:sale_id>/", views.edit_sale, name="edit_sale"),
    path("sales/void/<int:sale_id>/", views.void_sale, name="void_sale"),
    path("sales/delete/<int:sale_id>/", views.delete_sale, name="delete_sale"),

    #receipt view
    path("receipts/", views.receipts_list, name="receipts_list"),
    path("receipts/<int:sale_id>/", views.sale_receipt, name="sale_receipt"),
    path("receipts/detail/<int:sale_id>/", views.sale_receipt, name="receipt_detail"),
    path("receipts/print/<int:sale_id>/", views.receipt_print, name="receipt_print"),
    path("deposit-receipts/<int:deposit_id>/", views.deposit_receipt, name="deposit_receipt"),
    path("deposit-receipts/print/<int:deposit_id>/", views.deposit_receipt_print, name="deposit_receipt_print"),

    # supplier credit management
    path("supplier-credits/", views.credit_list, name="credit_list"), 
    path("supplier-credits/add/", views.add_credit, name="add_credit"),
    path("supplier-credits/edit/<int:pk>/", views.edit_credit, name="edit_credit"),
    path("supplier-credits/delete/<int:pk>/", views.delete_credit, name="delete_credit"),
    

    # deposit scheme management
    path("deposit-schemes/", views.deposit_list, name="deposit_list"),
    path("deposit-schemes/add/", views.add_deposit, name="add_deposit"),
    path("deposit-schemes/edit/<int:pk>/", views.edit_deposit, name="edit_deposit"),
    path("deposit-schemes/delete/<int:pk>/", views.delete_deposit, name="delete_deposit"),

    # reporting
     # reports
    path("sales-report/", views.sales_report, name="sales_report"),
    path("stock-report/", views.stock_report, name="stock_report"),
    path("profit-report/", views.profit_report, name="profit_report"),
    path("deposit-report/", views.deposit_report, name="deposit_report"),
    path("credit-report/", views.credit_report, name="credit_report"),
    path("audit-log/", views.audit_log, name="audit_log"),
    path("reports/", views.reports_home, name="reports_home"),

]

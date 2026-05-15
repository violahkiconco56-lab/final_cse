from django.db import models

# Create your models here.
class Stock(models.Model):

    CATEGORY_CHOICES = [
        ("Cement", "Cement"),
        ("Iron Bars", "Iron Bars"),
        ("Nails", "Nails"),
        ("Iron Sheets", "Iron Sheets"),
        ("Wire Mesh", "Wire Mesh"),
        ("Barbed Wire", "Barbed Wire"),
        ("Wheelbarrows", "Wheelbarrows"),
        ("Other", "Other"),
    ]

    product_name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    quantity = models.PositiveIntegerField()

    buying_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)

    supplier_name = models.CharField(max_length=100)

    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product_name
    
class Sales(models.Model):

    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=15)

    product_name = models.CharField(max_length=100)

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    distance_km = models.PositiveIntegerField()

    transport_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    PAYMENT_STATUS = [
        ("Paid", "Paid"),
        ("Pending", "Pending"),
    ]

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS
    )

    sale_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.customer_name
    
class SupplierCredit(models.Model):

    supplier_name = models.CharField(max_length=100)
    product_name = models.CharField(max_length=100)

    amount_owed = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    balance = models.DecimalField(max_digits=12, decimal_places=2)

    due_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.supplier_name
    
# class DepositScheme(models.Model):

#     customer_name = models.CharField(max_length=100)
#     nin_number = models.CharField(max_length=20)
#     phone_number = models.CharField(max_length=15)

#     product_name = models.CharField(max_length=100)

#     amount_deposited = models.DecimalField(max_digits=12, decimal_places=2)

#     balance = models.DecimalField(max_digits=12, decimal_places=2)

#     registration_date = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.customer_name
    
# # models.py

# from django.contrib.auth.models import User
# from django.db import models


# class AuditLog(models.Model):

#     ACTION_TYPES = [
#         ("LOGIN", "Login"),
#         ("LOGOUT", "Logout"),
#         ("CREATE", "Create"),
#         ("UPDATE", "Update"),
#         ("DELETE", "Delete"),
#         ("SALE", "Sale"),
#         ("STOCK", "Stock"),
#         ("CREDIT", "Credit"),
#     ]

#     user = models.ForeignKey(User, on_delete=models.CASCADE)

#     action = models.CharField(max_length=20, choices=ACTION_TYPES)

#     description = models.TextField()

#     timestamp = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.user.username} - {self.action}"

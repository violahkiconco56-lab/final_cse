from django.db import models

# Create your models here.
from django.db import models


class Stock(models.Model):

    # Product categories
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

    # Product name
    product_name = models.CharField(max_length=100)

    # Product category
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    # Number of items available
    quantity = models.PositiveIntegerField()

    # Minimum stock before warning
    reorder_level = models.PositiveIntegerField(default=5)

    # Buying price from supplier
    buying_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Selling price to customers
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Supplier/company name
    supplier_name = models.CharField(max_length=100)

    # Optional product description
    description = models.TextField(
        blank=True,
        null=True
    )

    # Automatically saves when product was added
    date_added = models.DateTimeField(auto_now_add=True)

    # Automatically updates when edited
    updated_at = models.DateTimeField(auto_now=True)

    # BUSINESS LOGIC

    # Profit from one item
    @property
    def profit_per_item(self):
        return self.selling_price - self.buying_price

    # Total possible profit
    @property
    def total_profit(self):
        return self.profit_per_item * self.quantity

    # Total stock value
    @property
    def stock_value(self):
        return self.selling_price * self.quantity

    # Check stock condition
    @property
    def stock_status(self):

        # No stock left
        if self.quantity == 0:
            return "OUT OF STOCK"

        # Very low stock
        elif self.quantity < 5:
            return "CRITICAL"

        # Warning level
        elif self.quantity <= 10:
            return "LOW"

        # Healthy stock
        return "OK"

    # String shown in admin panel
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

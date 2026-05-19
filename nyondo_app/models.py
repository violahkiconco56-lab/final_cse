from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
import uuid
from django.contrib.auth.models import User


# =========================
# STOCK MODEL
# =========================

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
    reorder_level = models.PositiveIntegerField(default=5)

    buying_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)

    supplier_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # BUSINESS LOGIC

    @property
    def profit_per_item(self):
        return self.selling_price - self.buying_price

    @property
    def total_profit(self):
        return self.profit_per_item * self.quantity

    @property
    def stock_value(self):
        return self.selling_price * self.quantity

    @property
    def stock_status(self):
        if self.quantity == 0:
            return "OUT OF STOCK"
        elif self.quantity <= self.reorder_level:
            return "LOW"
        return "OK"

    def __str__(self):
        return self.product_name


# =========================
# SALES MODEL
# =========================

class Sales(models.Model):

    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=15)

    product = models.ForeignKey(Stock, on_delete=models.PROTECT)

    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    distance_km = models.PositiveIntegerField(default=0)

    PAYMENT_STATUS = [
        ("Paid", "Paid"),
        ("Pending", "Pending"),
    ]

    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS)

    sale_date = models.DateTimeField(auto_now_add=True)

    receipt_no = models.CharField(max_length=20, unique=True, blank=True, editable=False)

    # BUSINESS LOGIC

    @property
    def total_amount(self):
        return self.quantity * self.unit_price

    @property
    def transport_charge(self):
        if self.distance_km <= 10 and self.total_amount >= 500000:
            return 0
        return 30000

    @property
    def final_total(self):
        return self.total_amount + self.transport_charge

    @property
    def profit(self):
        return (self.unit_price - self.product.buying_price) * self.quantity

    # VALIDATION

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")

        if self.distance_km < 0:
            raise ValidationError("Distance cannot be negative")

    # SAVE

    def save(self, *args, **kwargs):
        if not self.receipt_no:
            self.receipt_no = uuid.uuid4().hex[:10].upper()

        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_name} - {self.product.product_name}"


# =========================
# SUPPLIER
# =========================

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# =========================
# SUPPLIER CREDIT (FIXED - NO DUPLICATES)
# =========================

class SupplierCredit(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Cleared", "Cleared"),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)

    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)

    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    notes = models.TextField(blank=True, null=True)

    date_supplied = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        self.total_cost = self.unit_cost * self.quantity
        self.balance = self.total_cost - self.amount_paid

        if self.balance <= 0:
            self.balance = 0
            self.status = "Cleared"
        else:
            self.status = "Pending"

        super().save(*args, **kwargs)

    def payment_progress(self):
        if self.total_cost > 0:
            return (self.amount_paid / self.total_cost) * 100
        return 0

    def __str__(self):
        return f"{self.supplier.name} - {self.product_name}"


# =========================
# DEPOSIT SCHEME
# =========================

class DepositScheme(models.Model):

    customer_name = models.CharField(max_length=100)
    nin_number = models.CharField(max_length=20, unique=True)

    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                r'^(?:\+256|0)[0-9]{9}$',
                "Enter a valid Ugandan phone number."
            )
        ]
    )

    PRODUCT_CHOICES = [
        ("Cement", "Cement"),
        ("Iron Sheets", "Iron Sheets"),
        ("Iron Bars", "Iron Bars"),
    ]

    product_name = models.CharField(max_length=50, choices=PRODUCT_CHOICES)

    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(default=1)

    amount_deposited = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    registration_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_cost(self):
        return self.unit_price * self.quantity

    @property
    def balance(self):
        return max(self.total_cost - self.amount_deposited, 0)

    @property
    def status(self):
        if self.balance <= 0:
            return "Cleared"
        elif self.amount_deposited > 0:
            return "Partial"
        return "Pending"

    def __str__(self):
        return f"{self.customer_name} - {self.product_name}"
    
# tracking user actions for audit purposes
class AuditLog(models.Model):

    ACTION_TYPES = [
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("SALE", "Sale"),
        ("STOCK", "Stock"),
        ("CREDIT", "Credit"),
        ("DEPOSIT", "Deposit"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_TYPES
    )

    model_name = models.CharField(max_length=50, blank=True, null=True)

    object_id = models.CharField(max_length=50, blank=True, null=True)

    description = models.TextField()

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"   
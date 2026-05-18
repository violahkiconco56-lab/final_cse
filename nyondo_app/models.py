from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
import uuid
from django.core.exceptions import ValidationError

# Create your models here.


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
    
# SALES MODEL

class Sales(models.Model):

    # Customer details
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=15)

    # Product
    product = models.ForeignKey(
        "Stock",
        on_delete=models.PROTECT  # safer than CASCADE for sales records
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Transport input (distance only)
    distance_km = models.PositiveIntegerField(default=0)

    # Payment status
    PAYMENT_STATUS = [
        ("Paid", "Paid"),
        ("Pending", "Pending"),
    ]

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS
    )

    sale_date = models.DateTimeField(auto_now_add=True)

    # RECEIPT NUMBER
    receipt_no = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        editable=False
    )

    # =========================
    # BUSINESS LOGIC
    # =========================

    @property
    def total_amount(self):
        return self.quantity * self.unit_price

    @property
    def transport_charge(self):

        # FREE delivery rule
        if self.distance_km <= 10 and self.total_amount >= 500000:
            return 0

        return 30000

    @property
    def final_total(self):
        return self.total_amount + self.transport_charge

    @property
    def profit(self):
        return (
            (self.unit_price - self.product.buying_price)
            * self.quantity
        )

    # =========================
    # VALIDATION (IMPORTANT)
    # =========================
    def clean(self):

        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")

        if self.distance_km < 0:
            raise ValidationError("Distance cannot be negative")

    # =========================
    # SAVE OVERRIDE
    # =========================
    def save(self, *args, **kwargs):

        # Generate receipt number
        if not self.receipt_no:
            self.receipt_no = uuid.uuid4().hex[:10].upper()

        # Run validations
        self.clean()

        super().save(*args, **kwargs)

    # =========================
    # DISPLAY
    # =========================
    def __str__(self):
        return f"{self.customer_name} - {self.product.product_name}"

    # =========================
    # RECEIPT TEXT
    # =========================
    def receipt(self):
        return {
            "receipt_no": self.receipt_no,
            "customer": self.customer_name,
            "phone": self.customer_phone,
            "product": self.product.product_name,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total": float(self.total_amount),
            "transport": float(self.transport_charge),
            "final_total": float(self.final_total),
            "status": self.payment_status,
            "date": self.sale_date,
        }

# SUPPLIER CREDIT MODEL

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class SupplierCredit(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Cleared", "Cleared"),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)   


class SupplierCredit(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Cleared", "Cleared"),
    ]

    # Supplier linked to this credit
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE
    )

    # Product details
    product_name = models.CharField( max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    # Total debt
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Money already paid
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Remaining balance
    balance = models.DecimalField( max_digits=15, decimal_places=2, default=0)
    # Credit status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    # Optional notes
    notes = models.TextField(blank=True,  null=True )
    # Dates
    date_supplied = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # BUSINESS LOGIC
    def save(self, *args, **kwargs):

        # Calculate total cost
        self.total_cost = (
            self.unit_cost * self.quantity
        )

        # Calculate remaining balance
        self.balance = (
            self.total_cost - self.amount_paid
        )

        # Auto update status
        if self.balance <= 0:
            self.status = "Cleared"
            self.balance = 0

        else:
            self.status = "Pending"

        super().save(*args, **kwargs)

    # Percentage paid
    @property
    def payment_progress(self):

        if self.total_cost > 0:
            return (
                self.amount_paid / self.total_cost
            ) * 100

        return 0

    def __str__(self):
        return f"{self.supplier.name} - {self.product_name}"

# DEPOSIT SCHEME MODEL

class DepositScheme(models.Model):

    # Customer validation info
    customer_name = models.CharField(max_length=100)
    nin_number = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15, validators=[RegexValidator(r'^(?:\+256|0)[0-9]{9}$', "Enter a valid Ugandan phone number.")])

    # Product selection
    PRODUCT_CHOICES = [
        ("Cement", "Cement"),
        ("Iron Sheets", "Iron Sheets"),
        ("Iron Bars", "Iron Bars"),
    ]
    product_name = models.CharField(max_length=50, choices=PRODUCT_CHOICES)

    # Pricing structure
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    quantity = models.PositiveIntegerField(default=1)

    # Deposits
    amount_deposited = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Dates
    registration_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Business calculations
    @property
    def total_cost(self):
        return self.unit_price * self.quantity

    @property
    def balance(self):
        bal = self.total_cost - self.amount_deposited
        return max(bal, 0)

    @property
    def status(self):
        if self.balance <= 0:
            return "Cleared"
        elif self.amount_deposited > 0:
            return "Partial"
        return "Pending"

    def __str__(self):
        return f"{self.customer_name} - {self.product_name}"

    def receipt(self):
        return f"Receipt: {self.customer_name} deposited {self.amount_deposited} UGX for {self.product_name}."

    

    

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

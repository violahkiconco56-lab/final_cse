from django.db import models
from django.db import transaction
from django.db.models import F
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
import uuid
from django.contrib.auth.models import User


# STOCK MODEL

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

    @classmethod
    def low_stock_items(cls):
        return cls.objects.filter(quantity__lte=F("reorder_level")).order_by("quantity")

    @classmethod
    def low_stock_count(cls):
        return cls.low_stock_items().count()

    def clean(self):
        errors = {}

        if self.product_name:
            self.product_name = self.product_name.strip()
        if self.supplier_name:
            self.supplier_name = self.supplier_name.strip()

        if not self.product_name:
            errors["product_name"] = "Product name is required."
        if not self.supplier_name:
            errors["supplier_name"] = "Supplier name is required."
        if self.buying_price is not None and self.buying_price < 0:
            errors["buying_price"] = "Buying price cannot be negative."
        if self.selling_price is not None and self.selling_price < 0:
            errors["selling_price"] = "Selling price cannot be negative."
        if (
            self.buying_price is not None
            and self.selling_price is not None
            and self.selling_price < self.buying_price
        ):
            errors["selling_price"] = "Selling price cannot be lower than buying price."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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
        errors = {}

        if self.customer_name:
            self.customer_name = self.customer_name.strip()
        if self.customer_phone:
            self.customer_phone = self.customer_phone.strip()

        if not self.customer_name:
            errors["customer_name"] = "Customer name is required."
        if self.customer_phone and not self.customer_phone.isdigit():
            errors["customer_phone"] = "Phone number should contain digits only."
        if self.customer_phone and len(self.customer_phone) < 10:
            errors["customer_phone"] = "Phone number must be at least 10 digits."
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than 0."
        if self.unit_price is not None and self.unit_price < 0:
            errors["unit_price"] = "Unit price cannot be negative."
        if self.distance_km is not None and self.distance_km < 0:
            errors["distance_km"] = "Distance cannot be negative."
        if self.product_id and self.quantity:
            available_quantity = self.product.quantity
            if self.pk:
                previous_sale = Sales.objects.filter(pk=self.pk).first()
                if previous_sale and previous_sale.product_id == self.product_id:
                    available_quantity += previous_sale.quantity

            if self.quantity > available_quantity:
                errors["quantity"] = (
                    f"Not enough stock available. Available: {available_quantity}, "
                    f"requested: {self.quantity}."
                )

        if errors:
            raise ValidationError(errors)

    # SAVE

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.receipt_no:
                self.receipt_no = uuid.uuid4().hex[:10].upper()

            self.full_clean()

            previous_sale = None
            if self.pk:
                previous_sale = Sales.objects.select_related("product").filter(pk=self.pk).first()

            if self.pk and previous_sale:
                if self.product == previous_sale.product:
                    stock_change = self.quantity - previous_sale.quantity
                    if stock_change > 0 and stock_change > self.product.quantity:
                        raise ValidationError(
                            f"Not enough stock available. Available: {self.product.quantity}, requested change: {stock_change}"
                        )
                    self.product.quantity -= stock_change
                    self.product.save()
                else:
                    old_product = previous_sale.product
                    old_product.quantity += previous_sale.quantity
                    old_product.save()

                    if self.quantity > self.product.quantity:
                        raise ValidationError(
                            f"Not enough stock available. Available: {self.product.quantity}, requested: {self.quantity}"
                        )
                    self.product.quantity -= self.quantity
                    self.product.save()
            else:
                if self.quantity > self.product.quantity:
                    raise ValidationError(
                        f"Not enough stock available. Available: {self.product.quantity}, requested: {self.quantity}"
                    )
                self.product.quantity -= self.quantity
                self.product.save()

            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            product = self.product
            product.quantity += self.quantity
            product.save()
            super().delete(*args, **kwargs)

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

    def clean(self):
        errors = {}

        if self.name:
            self.name = self.name.strip()
        if self.contact:
            self.contact = self.contact.strip()

        if not self.name:
            errors["name"] = "Supplier name is required."
        if self.contact and not self.contact.isdigit():
            errors["contact"] = "Supplier contact should contain digits only."
        if self.contact and len(self.contact) < 10:
            errors["contact"] = "Supplier contact must be at least 10 digits."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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

    def clean(self):
        errors = {}

        if self.product_name:
            self.product_name = self.product_name.strip()

        if not self.product_name:
            errors["product_name"] = "Product name is required."
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than 0."
        if self.unit_cost is not None and self.unit_cost < 0:
            errors["unit_cost"] = "Unit cost cannot be negative."
        if self.amount_paid is not None and self.amount_paid < 0:
            errors["amount_paid"] = "Amount paid cannot be negative."
        if self.quantity and self.unit_cost is not None and self.amount_paid is not None:
            total_cost = self.quantity * self.unit_cost
            if self.amount_paid > total_cost:
                errors["amount_paid"] = "Amount paid cannot exceed total cost."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()

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

    def clean(self):
        errors = {}

        if self.customer_name:
            self.customer_name = self.customer_name.strip()
        if self.nin_number:
            self.nin_number = self.nin_number.strip().upper()
        if self.phone_number:
            self.phone_number = self.phone_number.strip()

        if not self.customer_name:
            errors["customer_name"] = "Customer name is required."
        if not self.nin_number:
            errors["nin_number"] = "NIN is required."
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than 0."
        if self.unit_price is not None and self.unit_price < 0:
            errors["unit_price"] = "Unit price cannot be negative."
        if self.amount_deposited is not None and self.amount_deposited < 0:
            errors["amount_deposited"] = "Amount deposited cannot be negative."
        if self.unit_price is not None and self.quantity and self.amount_deposited is not None:
            total_cost = self.unit_price * self.quantity
            if self.amount_deposited > total_cost:
                errors["amount_deposited"] = "Deposit cannot exceed total cost."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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

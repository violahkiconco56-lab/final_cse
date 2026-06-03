from django import forms
from .models import Stock, Sales, SupplierCredit, DepositScheme, Supplier
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm


# Stock form
class StockForm(forms.ModelForm):

    class Meta:
        model = Stock
        fields = [
            "product_name",
            "category",
            "quantity",
            "buying_price",
            "selling_price",
            "supplier_name",
            "description",
            "reorder_level",
        ]

        widgets = {
            "product_name": forms.TextInput(attrs={"placeholder": "Enter product name"}),
            "category": forms.Select(),
            "quantity": forms.NumberInput(attrs={"min": 0}),
            "buying_price": forms.NumberInput(attrs={"step": "0.01"}),
            "selling_price": forms.NumberInput(attrs={"step": "0.01"}),
            "supplier_name": forms.TextInput(attrs={"placeholder": "Supplier name"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "reorder_level": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative")
        return quantity

    def clean_product_name(self):
        return (self.cleaned_data.get("product_name") or "").strip()

    def clean_supplier_name(self):
        return (self.cleaned_data.get("supplier_name") or "").strip()

    def clean(self):
        cleaned_data = super().clean()

        buying_price = cleaned_data.get("buying_price")
        selling_price = cleaned_data.get("selling_price")
        reorder_level = cleaned_data.get("reorder_level")

        if buying_price is not None and buying_price < 0:
            self.add_error("buying_price", "Buying price cannot be negative")

        if selling_price is not None and selling_price < 0:
            self.add_error("selling_price", "Selling price cannot be negative")

        if reorder_level is not None and reorder_level < 0:
            self.add_error("reorder_level", "Reorder level cannot be negative")

        if buying_price is not None and selling_price is not None:
            if selling_price < buying_price:
                self.add_error(
                    "selling_price",
                    "Selling price cannot be lower than buying price"
                )

        return cleaned_data


# Supplier credit form
class SupplierCreditForm(forms.ModelForm):

    class Meta:
        model = SupplierCredit
        fields = [
            "supplier",
            "product_name",
            "quantity",
            "unit_cost",
            "amount_paid",
            "notes",
        ]

        widgets = {
            "supplier": forms.Select(attrs={"class": "form-select"}),
            "product_name": forms.TextInput(attrs={"placeholder": "Item name"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "unit_cost": forms.NumberInput(attrs={"step": "0.01"}),
            "amount_paid": forms.NumberInput(attrs={"step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_product_name(self):
        return (self.cleaned_data.get("product_name") or "").strip()

    def clean(self):
        cleaned_data = super().clean()

        quantity = cleaned_data.get("quantity")
        unit_cost = cleaned_data.get("unit_cost")
        amount_paid = cleaned_data.get("amount_paid") or 0

        if quantity is not None and quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than 0.")

        if unit_cost is not None and unit_cost < 0:
            self.add_error("unit_cost", "Unit cost cannot be negative.")

        if amount_paid is not None and amount_paid < 0:
            self.add_error("amount_paid", "Amount paid cannot be negative.")

        if quantity and unit_cost:
            total_cost = quantity * unit_cost

            if amount_paid > total_cost:
                self.add_error(
                    "amount_paid",
                    "Amount paid cannot exceed total cost."
                )

        return cleaned_data


class SupplierForm(forms.ModelForm):

    class Meta:
        model = Supplier
        fields = ["name", "contact", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Supplier name"}),
            "contact": forms.TextInput(attrs={"placeholder": "Phone or contact"}),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Supplier address"}),
        }

    def clean_name(self):
        return (self.cleaned_data.get("name") or "").strip()

    def clean_contact(self):
        return (self.cleaned_data.get("contact") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        contact = cleaned_data.get("contact")

        if contact and not contact.isdigit():
            self.add_error("contact", "Supplier contact should contain digits only")
        if contact and len(contact) < 10:
            self.add_error("contact", "Supplier contact must be at least 10 digits")

        return cleaned_data


class SupplierForm(forms.ModelForm):

    class Meta:
        model = Supplier
        fields = ["name", "contact", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Supplier name"}),
            "contact": forms.TextInput(attrs={"placeholder": "Phone or contact"}),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Supplier address"}),
        }

    def clean_name(self):
        return (self.cleaned_data.get("name") or "").strip()

    def clean_contact(self):
        return (self.cleaned_data.get("contact") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        contact = cleaned_data.get("contact")

        if contact and not contact.isdigit():
            self.add_error("contact", "Supplier contact should contain digits only")
        if contact and len(contact) < 10:
            self.add_error("contact", "Supplier contact must be at least 10 digits")

        return cleaned_data


# Deposit form
class DepositSchemeForm(forms.ModelForm):

    class Meta:
        model = DepositScheme
        fields = [
            "customer_name",
            "nin_number",
            "phone_number",
            "product_name",
            "unit_price",
            "quantity",
            "amount_deposited",
        ]

        widgets = {
            "customer_name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "nin_number": forms.TextInput(attrs={"placeholder": "National ID"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "Phone number"}),
            "product_name": forms.Select(),
            "unit_price": forms.NumberInput(attrs={"step": "0.01", "min": 0}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "amount_deposited": forms.NumberInput(attrs={"step": "0.01", "min": 0}),
        }

    def clean_customer_name(self):
        return (self.cleaned_data.get("customer_name") or "").strip()

    def clean_nin_number(self):
        nin = (self.cleaned_data.get("nin_number") or "").strip().upper()

        qs = DepositScheme.objects.filter(nin_number=nin)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("NIN already exists.")

        return nin

    def clean(self):
        cleaned_data = super().clean()

        unit_price = cleaned_data.get("unit_price")
        quantity = cleaned_data.get("quantity")
        amount = cleaned_data.get("amount_deposited") or 0

        if unit_price is not None and unit_price < 0:
            self.add_error("unit_price", "Unit price cannot be negative.")

        if quantity is not None and quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than 0.")

        if amount is not None and amount < 0:
            self.add_error("amount_deposited", "Amount deposited cannot be negative.")

        if unit_price and quantity:
            total_cost = unit_price * quantity

            if amount > total_cost:
                self.add_error(
                    "amount_deposited",
                    "Deposit cannot exceed total cost."
                )

        return cleaned_data


# Sale form (fixed and simplified)
class SaleForm(forms.ModelForm):

    class Meta:
        model = Sales
        fields = [
            "customer_name",
            "customer_phone",
            "product",
            "quantity",
            "unit_price",
            "distance_km",
            "payment_status",
        ]

        error_messages = {
            "customer_name": {"required": "Customer name is required."},
            "customer_phone": {"required": "Phone number is required."},
            "product": {"required": "Please select a product."},
            "quantity": {"required": "Quantity is required."},
            "unit_price": {"required": "Unit price is required."},
            "distance_km": {"required": "Distance is required."},
            "payment_status": {"required": "Payment status is required."},
        }

        widgets = {
            "customer_name": forms.TextInput(attrs={"placeholder": "Customer name"}),
            "customer_phone": forms.TextInput(attrs={"placeholder": "Phone number"}),
            "product": forms.Select(attrs={"required": "required"}),
            "quantity": forms.NumberInput(attrs={"min": 1, "required": "required"}),
            "unit_price": forms.NumberInput(attrs={"step": "0.01", "min": 0, "readonly": "readonly", "required": "required"}),
            "distance_km": forms.NumberInput(attrs={"min": 0, "placeholder": "Distance in KM", "required": "required"}),
            "payment_status": forms.Select(attrs={"required": "required"}),
        }

    def clean_customer_name(self):
        return (self.cleaned_data.get("customer_name") or "").strip()

    def clean_customer_phone(self):
        phone = (self.cleaned_data.get("customer_phone") or "").strip()

        if phone and not phone.isdigit():
            raise forms.ValidationError("Phone number should contain digits only")
        if phone and len(phone) < 10:
            raise forms.ValidationError("Phone number must be at least 10 digits")

        return phone

    def clean_distance_km(self):
        distance = self.cleaned_data.get("distance_km")

        if distance is None:
            raise forms.ValidationError("Distance is required.")
        if distance < 0:
            raise forms.ValidationError("Distance cannot be negative.")

        return distance

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity")
        distance = cleaned_data.get("distance_km")
        unit_price = cleaned_data.get("unit_price")

        if quantity is not None and quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than 0")

        if unit_price is not None and unit_price < 0:
            self.add_error("unit_price", "Unit price cannot be negative")

        if distance is not None and distance < 0:
            self.add_error("distance_km", "Distance cannot be negative")

        if product and quantity:
            available_quantity = product.quantity

            if self.instance.pk and self.instance.product_id == product.id:
                available_quantity += self.instance.quantity

            if quantity > available_quantity:
                self.add_error(
                    "quantity",
                    f"Not enough stock. Available: {available_quantity}"
                )

        # auto-set correct selling price
        if product:
            cleaned_data["unit_price"] = product.selling_price

        return cleaned_data


# User creation form
class CustomUserCreationForm(UserCreationForm):

    ROLE_CHOICES = (
        ("", "--- Select Role ---"),
        ("sales", "Sales"),
        ("stock", "Stock"),
        ("admin", "Admin"),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES, 
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        # Explicitly list fields to ensure they appear in the correct order
        fields = ("username", "role")

    def save(self, commit=True):
        user = super().save(commit=False) # Get the user instance, but don't save it yet
        if commit: # If commit is True, save the user and then add to group
            user.save() # Save the user to the database
            role = self.cleaned_data.get("role") # Get the selected role
            group, created = Group.objects.get_or_create(name=role) # Get or create the group
            user.groups.add(group) # Add the user to the group
        else: # If commit is False, the user is not saved, so group assignment cannot happen yet
            # You might want to handle this case or ensure commit is always True for this form
            pass 
        return user # Return the user instance

from django import forms
from .models import Stock, SupplierCredit, DepositScheme

# STOCK FORM (ADD + EDIT)
class StockForm(forms.ModelForm):
    """
    Handles:
    - Add Stock (Create)
    - Edit Stock (Update)
    - Ensures clean inventory input
    """

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

        
        # UI ENHANCEMENT (UX IMPROVEMENT)
        widgets = {

            "product_name": forms.TextInput(attrs={
                "placeholder": "Enter product name"
            }),

            "category": forms.Select(),

            "quantity": forms.NumberInput(attrs={
                "min": 0,
                "placeholder": "Quantity in stock"
            }),

            "buying_price": forms.NumberInput(attrs={
                "step": "0.01",
                "placeholder": "Buying price (UGX)"
            }),

            "selling_price": forms.NumberInput(attrs={
                "step": "0.01",
                "placeholder": "Selling price (UGX)"
            }),

            "supplier_name": forms.TextInput(attrs={
                "placeholder": "Supplier name"
            }),

            "description": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Optional product details"
            }),

            "reorder_level": forms.NumberInput(attrs={
                "min": 0,
                "placeholder": "Low stock warning level"
            }),
        }

    # VALIDATION RULES
    def clean_quantity(self):
        """
        Prevents negative stock values
        """
        quantity = self.cleaned_data.get("quantity")

        if quantity is not None and quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative")

        return quantity

    def clean(self):
        """
        Business logic validation:
        Selling price must not be lower than buying price
        """

        cleaned_data = super().clean()

        buying_price = cleaned_data.get("buying_price")
        selling_price = cleaned_data.get("selling_price")

        if buying_price and selling_price:
            if selling_price < buying_price:
                raise forms.ValidationError(
                    "Selling price cannot be lower than buying price"
                )
        return cleaned_data

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
            "item_name": forms.TextInput(attrs={"placeholder": "Item name"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "unit_cost": forms.NumberInput(attrs={"step": "0.01"}),
            "amount_paid": forms.NumberInput(attrs={"step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "supplier": forms.Select(attrs={"placeholder": "Choose supplier"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get("quantity")
        unit_cost = cleaned_data.get("unit_cost")
        amount_paid = cleaned_data.get("amount_paid")

        if quantity and unit_cost and amount_paid is not None:
           total_cost = quantity * unit_cost
        if amount_paid > total_cost:
           raise forms.ValidationError("Amount paid cannot exceed total cost.")
        return cleaned_data
    

class DepositSchemeForm(forms.ModelForm):
    """
    Handles:
    - Add Deposit Scheme (Create)
    - Edit Deposit Scheme (Update)
    - Validates customer + financial rules
    """

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
            "customer_name": forms.TextInput(attrs={
                "placeholder": "Full name"
            }),

            "nin_number": forms.TextInput(attrs={
                "placeholder": "National ID Number"
            }),

            "phone_number": forms.TextInput(attrs={
                "placeholder": "Phone number"
            }),

            "product_name": forms.Select(),

            "unit_price": forms.NumberInput(attrs={
                "step": "0.01",
                "min": 0,
                "placeholder": "Unit price"
            }),

            "quantity": forms.NumberInput(attrs={
                "min": 1,
                "placeholder": "Quantity"
            }),

            "amount_deposited": forms.NumberInput(attrs={
                "step": "0.01",
                "min": 0,
                "placeholder": "Amount deposited"
            }),
        }

    # VALIDATION RULE 1 (DATA INTEGRITY)
    def clean_nin_number(self):

        nin = self.cleaned_data.get("nin_number")

        qs = DepositScheme.objects.filter(
            nin_number=nin
        )

        # NEW CHANGE
        # Ignore current record during editing
        if self.instance.pk:
            qs = qs.exclude(
                pk=self.instance.pk
            )

        # NEW CHANGE
        # Prevent duplicate NINs
        if qs.exists():
            raise forms.ValidationError(
                "Customer with this NIN already exists."
            )

        return nin
    # VALIDATION RULE 2 (BUSINESS LOGIC)
    def clean(self):

        cleaned_data = super().clean()

        unit_price = cleaned_data.get("unit_price")
        quantity = cleaned_data.get("quantity")
        amount = cleaned_data.get("amount_deposited")


        # Prevent deposit exceeding total cost
        if unit_price and quantity:

            total_cost = unit_price * quantity

            if amount is not None and amount > total_cost:

                raise forms.ValidationError(
                    "Amount deposited cannot exceed total cost."
                )

        return cleaned_data
    
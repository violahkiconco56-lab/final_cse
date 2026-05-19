from django import forms
from .models import Stock, SupplierCredit, DepositScheme

# STOCK FORM (ADD + EDIT)
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

    def clean(self):
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
            "supplier": forms.Select(),
            "product_name": forms.TextInput(attrs={"placeholder": "Item name"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "unit_cost": forms.NumberInput(attrs={"step": "0.01"}),
            "amount_paid": forms.NumberInput(attrs={"step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()

        quantity = cleaned_data.get("quantity")
        unit_cost = cleaned_data.get("unit_cost")
        amount_paid = cleaned_data.get("amount_paid") or 0

        if quantity and unit_cost:
            total_cost = quantity * unit_cost

            if amount_paid > total_cost:
                raise forms.ValidationError(
                    "Amount paid cannot exceed total cost."
                )

        return cleaned_data
    
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

    def clean_nin_number(self):
        nin = self.cleaned_data.get("nin_number")

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

        if unit_price and quantity:
            total_cost = unit_price * quantity

            if amount > total_cost:
                raise forms.ValidationError(
                    "Deposit cannot exceed total cost."
                )

        return cleaned_data
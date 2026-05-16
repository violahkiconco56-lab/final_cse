from django import forms
from .models import Stock


# ==========================
# STOCK FORM (ADD + EDIT)
# ==========================
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

        # ==========================
        # UI ENHANCEMENT (UX IMPROVEMENT)
        # ==========================
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

    # ==========================
    # VALIDATION RULES
    # ==========================

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
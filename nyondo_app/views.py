from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages
from django.db.models import DecimalField, ExpressionWrapper, Sum, F, Q, Count
from django.core.exceptions import ValidationError

from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.db.models.functions import TruncMonth
from django.db import transaction
from .models import Stock, Sales, SupplierCredit, DepositScheme, Supplier, AuditLog
from .forms import StockForm, SaleForm, SupplierCreditForm, DepositSchemeForm, SupplierForm, CustomUserCreationForm

def log_audit(user, action, description, model_name=None, object_id=None):
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else None,
        description=description,
    )


def get_low_stock_notification():
    low_items = Stock.low_stock_items()
    count = low_items.count()
    return {
        "low_stock_alert_items": low_items,
        "low_stock_alert_count": count,
        "low_stock_alert_message": (
            f"{count} product{'s' if count != 1 else ''} are at or below reorder level"
            if count else "All stock levels are healthy"
        ),
    }





# Create your views here.
def register_view(request):

    if request.method == "POST":

        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            new_user = form.save() # This triggers the custom save() in forms.py
            log_audit(
                request.user, # The superuser performing the registration
                "CREATE",
                f"Registered user {new_user.username}",
                model_name="auth.User",
                object_id=new_user.pk,
            )

            messages.success(
                request,
                "Account created successfully."
            )

            return redirect("register")

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")

    else:

        form = CustomUserCreationForm()

    users = User.objects.prefetch_related('groups').all().order_by("-id")

    context = {
        "form": form,
        "users": users,
    }

    return render(
        request,
        "accounts/register.html",
        context
    )

@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    user_to_delete = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        if user_to_delete == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect("register")

        # Prevent deleting the last superuser
        if user_to_delete.is_superuser:
            remaining_superusers = User.objects.filter(is_superuser=True).exclude(pk=user_to_delete.pk).count()
            if remaining_superusers == 0:
                messages.error(request, "Cannot delete the last superuser.")
                return redirect("register")

        username = user_to_delete.username
        user_pk = user_to_delete.pk
        user_to_delete.delete()
        log_audit(
            request.user,
            "DELETE",
            f"Deleted user {username}",
            model_name="auth.User",
            object_id=user_pk,
        )
        messages.success(request, f"User {username} deleted successfully.")
        return redirect("register")

    # If it's a GET request, we'll just redirect back to the register page.
    # The confirmation is handled by JavaScript on the register.html page.
    return redirect("register")

@ensure_csrf_cookie
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            
            log_audit(
                user,
                "LOGIN",
                f"User {user.username} logged in",
                model_name="User",
                object_id=user.pk,
            )

            group_names = list(user.groups.values_list("name", flat=True))
            normalized_groups = [name.strip().lower() for name in group_names]

            if user.is_superuser:
                return redirect("admin_dashboard")
            # Accept both old and new group naming variations
            elif "sales attendant" in normalized_groups or "sales" in normalized_groups:
                return redirect("sales_dashboard")
            elif "store manager" in normalized_groups or "stock" in normalized_groups:
                return redirect("stock_dashboard")
            elif "accounts/admin" in normalized_groups or "admin" in normalized_groups:
                return redirect("admin_dashboard")
            else:
                messages.error(
                    request,
                    f"No role assigned. Groups found: {group_names}"
                )
                return redirect("login")
        else:
            messages.error(request, "Account not found, Please check your credentials and try again.")
            return redirect("login")

    return render(request, "accounts/login.html")    


def logout_view(request):
    if request.user.is_authenticated:
        log_audit(
            request.user,
            "LOGOUT",
            f"User {request.user.username} logged out",
            model_name="User",
            object_id=request.user.pk,
        )

    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")


# ==========================================
# 2. ADMIN DASHBOARD VIEW
# ==========================================

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("login")

    sales = Sales.objects.select_related("product").filter(is_voided=False)

    total_revenue = sales.aggregate(
        total=Sum(ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField()))
    )["total"] or 0

    total_profit = sales.aggregate(
        total=Sum(ExpressionWrapper((F("unit_price") - F("product__buying_price")) * F("quantity"), output_field=DecimalField()))
    )["total"] or 0

    total_orders = sales.count()

    stock_value = Stock.objects.aggregate(
        total=Sum(ExpressionWrapper(F("quantity") * F("selling_price"), output_field=DecimalField()))
    )["total"] or 0

    total_products = Stock.objects.count()
    stock_issues = Stock.objects.filter(quantity__lte=10).count()

    low_stock_alert = get_low_stock_notification()
    if low_stock_alert.get("low_stock_alert_count"):
        messages.warning(request, low_stock_alert["low_stock_alert_message"])
    alert_items = low_stock_alert.get("low_stock_alert_items", [])
    alert_count = low_stock_alert.get("low_stock_alert_count", 0)
    alert_msg = low_stock_alert.get("low_stock_alert_message", "")

    total_credit = SupplierCredit.objects.aggregate(total=Sum("balance"))["total"] or 0
    pending_credit = SupplierCredit.objects.filter(status="Pending").count()
    cleared_credit = SupplierCredit.objects.filter(status="Cleared").count()

    total_deposits = DepositScheme.objects.aggregate(total=Sum("amount_deposited"))["total"] or 0
    pending_deposits = DepositScheme.objects.filter(amount_deposited__lt=F("unit_price") * F("quantity")).count()
    completed_deposits = DepositScheme.objects.filter(amount_deposited__gte=F("unit_price") * F("quantity")).count()

    free_deliveries = Sales.objects.filter(is_voided=False, distance_km__lte=10).count()
    charged_deliveries = Sales.objects.filter(is_voided=False, distance_km__gt=10).count()

    recent_sales = sales.order_by("-sale_date")[:10]
    top_products = sales.values("product__product_name").annotate(total_sold=Sum("quantity")).order_by("-total_sold")[:5]

    recent_audits = AuditLog.objects.select_related("user").order_by("-timestamp")[:5]

    profit_margin = (total_profit / total_revenue * 100) if total_revenue else 0

    return render(request, "nyondo/admin_dashboard.html", {
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "profit_margin": round(profit_margin, 2),
        "total_orders": total_orders,
        "stock_value": stock_value,
        "total_products": total_products,
        "stock_issues": stock_issues,
        "low_stock_alert_items": alert_items,
        "low_stock_alert_count": alert_count,
        "low_stock_alert_message": alert_msg,
        "total_credit": total_credit,
        "pending_credit": pending_credit,
        "cleared_credit": cleared_credit,
        "total_deposits": total_deposits,
        "pending_deposits": pending_deposits,
        "completed_deposits": completed_deposits,
        "free_deliveries": free_deliveries,
        "charged_deliveries": charged_deliveries,
        "recent_audits": recent_audits,
        "recent_sales": recent_sales,
        "top_products": top_products,
    })


# ==========================================
# 3. STOCK DASHBOARD VIEW
# ==========================================

@login_required
def stock_dashboard(request):
    is_stock_user = request.user.groups.filter(name__iexact="stock").exists()
    if not (request.user.is_superuser or is_stock_user):
        messages.error(request, "Access denied. You do not have permissions for the Stock Dashboard.")
        return redirect("login")

    stock_products = Stock.objects.all()
    total_products = Stock.objects.count()

    inventory_value = Stock.objects.aggregate(
        total=Sum(ExpressionWrapper(F("quantity") * F("selling_price"), output_field=DecimalField()))
    )["total"] or 0

    low_stock = Stock.objects.filter(quantity__lte=10).count()
    out_of_stock = Stock.objects.filter(quantity=0).count()
    
    low_stock_alert = get_low_stock_notification()
    alert_items = low_stock_alert.get("low_stock_alert_items", [])
    alert_count = low_stock_alert.get("low_stock_alert_count", 0)
    alert_msg = low_stock_alert.get("low_stock_alert_message", "")

    total_profit = Stock.objects.aggregate(
        total=Sum(ExpressionWrapper((F("selling_price") - F("buying_price")) * F("quantity"), output_field=DecimalField()))
    )["total"] or 0

    context = {
        "stock_products": stock_products,
        "total_products": total_products,
        "inventory_value": inventory_value,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "low_stock_alert_items": alert_items,
        "low_stock_alert_count": alert_count,
        "low_stock_alert_message": alert_msg,
        "total_profit": total_profit,
    }
    return render(request, "nyondo/stock_dashboard.html", context)


# ==========================================
# 4. SALES DASHBOARD VIEW (FULLY COMPLETE)
# ==========================================

@login_required
def sales_dashboard(request):
    # 🔒 Security: Only allow sales group members or superusers
    is_sales_user = request.user.groups.filter(name__iexact="sales").exists()
    if not (request.user.is_superuser or is_sales_user):
        messages.error(request, "Access denied. You do not have permissions for the Sales Dashboard.")
        return redirect("login")

    # ================= BASIC KPIs =================
    sales = Sales.objects.select_related("product").filter(is_voided=False)

    total_sales = sales.count()
    
    # Use ORM aggregation for better performance
    aggregated_sales = sales.aggregate(
        total_revenue=Sum(
            ExpressionWrapper(F("quantity") * F("unit_price") + F("distance_km") * 3000, output_field=DecimalField())
            # Assuming 3000 is the transport charge per km for calculation, adjust if logic is different
        ),
        total_profit=Sum(
            ExpressionWrapper((F("unit_price") - F("product__buying_price")) * F("quantity"), output_field=DecimalField())
        )
    )
    total_revenue = aggregated_sales["total_revenue"] or 0
    total_profit = aggregated_sales["total_profit"] or 0

    total_customers = sales.values("customer_phone").distinct().count()
    
    pending_payments = sum(sale.final_total for sale in sales if sale.payment_status == 'Pending')

    # ================= TODAY SALES =================
    today = timezone.now().date()
    today_sales_qs = sales.filter(sale_date__date=today)
    today_sales_aggregated = today_sales_qs.aggregate(
        count=Count('id'),
        revenue=Sum(ExpressionWrapper(F("quantity") * F("unit_price") + F("distance_km") * 3000, output_field=DecimalField()))
    )
    today_sales = today_sales_aggregated["count"] or 0
    today_revenue = today_sales_aggregated["revenue"] or 0

    # ================= TOP PRODUCTS =================
    top_products = (
        sales.values(product_name=F("product__product_name"))
        .annotate(units_sold=Sum("quantity"))
        .order_by("-units_sold")[:5]
    )

    recent_sales = sales.order_by("-sale_date")[:10]
    low_stock = Stock.objects.filter(quantity__lte=10)

    context = {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "total_customers": total_customers,
        "pending_payments": pending_payments,
        "today_sales": today_sales,
        "today_revenue": today_revenue,
        "recent_sales": recent_sales,
        "top_products": top_products,
        "low_stock": low_stock,
    }

    return render(request, "nyondo/sales_dashboard.html", context)



# STOCK LIST SECTION
@login_required
def stock_list(request):

    # Get all stock items
    stocks = Stock.objects.all().order_by("-date_added")

    # Get search input
    query = request.GET.get("q")

    # Search by product name
    if query:
        stocks = stocks.filter(
            product_name__icontains=query
        )

    # Get filter option
    filter_type = request.GET.get("filter")

    # Show low stock only
    if filter_type == "low":
        stocks = stocks.filter(quantity__lte=10)

    # Show out of stock only
    elif filter_type == "out":
        stocks = stocks.filter(quantity=0)

    # Send data to template
    context = {
        "stocks": stocks,
        "query": query,
        "filter_type": filter_type,
    }

    return render(
        request,
        "nyondo/stock_list.html",
        context
    )


# ADD STOCK
@login_required
def add_stock(request):

    # Create empty form
    form = StockForm()

    # If form is submitted
    if request.method == "POST":

        # Bind form with submitted data
        form = StockForm(request.POST)

        # Validate form
        if form.is_valid():

            # Save stock to database
            stock = form.save()
            log_audit(
                request.user,
                "STOCK",
                f"Added stock {stock.product_name} ({stock.quantity})",
                model_name="Stock",
                object_id=stock.pk,
            )

            # Success message
            messages.success(
                request,
                f"{stock.product_name} added successfully."
            )

            # Redirect to stock list
            return redirect("stock_list")
        else:
            messages.error(request, "Please fix the errors below and try again.")

    # Send form to template
    return render(
        request,
        "nyondo/add_stock.html",
        {"form": form}
    )

# EDIT STOCK
@login_required
def edit_stock(request, stock_id):

    # Get stock item or 404i want
    stock = get_object_or_404(Stock, id=stock_id)

    # Load form with existing data
    form = StockForm(instance=stock)

    # If form submitted
    if request.method == "POST":

        # Bind form with POST + existing instance
        form = StockForm(request.POST, instance=stock)

        # Validate form
        if form.is_valid():

            # Save updates
            stock = form.save()
            log_audit(
                request.user,
                "STOCK",
                f"Updated stock {stock.product_name} ({stock.quantity})",
                model_name="Stock",
                object_id=stock.pk,
            )

            # Success message
            messages.success(
                request,
                f"{stock.product_name} updated successfully."
            )

            # Redirect
            return redirect("stock_list")

    return render(
        request,
        "nyondo/edit_stock.html",
        {"form": form, "stock": stock}
    )

# DELETE STOCK

@login_required
def delete_stock(request, stock_id):

    stock = get_object_or_404(Stock, id=stock_id)

    if request.method == "POST":

        name = stock.product_name
        log_audit(
            request.user,
            "DELETE",
            f"Deleted stock {name}",
            model_name="Stock",
            object_id=stock.pk,
        )
        stock.delete()

        messages.success(request, f"{name} deleted successfully")

        return redirect("stock_list")

    return render(request, "nyondo/delete_stock.html", {"stock": stock}) 



#sales list view

# SALES LIST
@login_required
def sales_list(request):

    query = request.GET.get("q")

    sales = Sales.objects.select_related("product").order_by("-sale_date")

    if query:
        sales = sales.filter(
            Q(customer_name__icontains=query) |
            Q(product__product_name__icontains=query) |
            Q(receipt_no__icontains=query)
        )

    return render(
        request,
        "nyondo/sales_list.html",
        {
            "sales": sales,
            "query": query
        }
    )


# ADD SALE
@login_required
def add_sale(request):

    products = Stock.objects.filter(quantity__gt=0).order_by("product_name")
    form = SaleForm()

    if request.method == "POST":
        action = request.POST.get("action")
        form = SaleForm(request.POST)

        # Always populate unit_price from the selected product in the server-side form
        selected_product_id = request.POST.get("product")
        if selected_product_id:
            try:
                product = Stock.objects.get(pk=selected_product_id)
                form.fields["unit_price"].initial = product.selling_price
                if form.is_bound:
                    data = form.data.copy()
                    data[form.add_prefix("unit_price")] = str(product.selling_price)
                    form.data = data
            except (Stock.DoesNotExist, ValueError):
                pass

        if action == "update_price":
            messages.info(request, "Selling price loaded from selected product.")
            return render(request, "nyondo/add_sales.html", {"form": form, "products": products})

        if form.is_valid():
            sale = form.save()
            log_audit(
                request.user,
                "SALE",
                f"Created sale {sale.receipt_no} for {sale.customer_name} ({sale.quantity} x {sale.product.product_name})",
                model_name="Sales",
                object_id=sale.pk,
            )

            messages.success(
                request,
                f"Sale created successfully. Receipt No: {sale.receipt_no}"
            )
            return redirect("sales_list")
        else:
            messages.error(request, "Please fix the errors below and try again.")

    return render(request, "nyondo/add_sales.html", {"form": form, "products": products})


# EDIT SALE
@login_required
def edit_sale(request, sale_id):

    sale = get_object_or_404(Sales, id=sale_id)
    if sale.is_voided:
        messages.error(request, "Voided sales cannot be edited.")
        return redirect("sales_list")

    form = SaleForm(instance=sale)

    if request.method == "POST":
        form = SaleForm(request.POST, instance=sale)

        if form.is_valid():
            sale = form.save()
            log_audit(
                request.user,
                "SALE",
                f"Updated sale {sale.receipt_no} for {sale.customer_name}",
                model_name="Sales",
                object_id=sale.pk,
            )

            messages.success(request, "Sale updated successfully.")
            return redirect("sales_list")

    return render(
        request,
        "nyondo/edit_sale.html",
        {"form": form, "sale": sale}
    )


# SALE RECEIPT (VIEW)
@login_required
def receipts_list(request):

    receipts = Sales.objects.all().order_by("-sale_date")

    return render(
        request,
        "nyondo/receipt_list.html",
        {"receipts": receipts}
    )

@login_required
def sale_receipt(request, sale_id):

    sale = get_object_or_404(Sales, id=sale_id)

    return render(
        request,
        "nyondo/receipt_details.html",
        {"receipt": sale}
    )

@login_required
def receipt_print(request, sale_id):

    sale = get_object_or_404(Sales, id=sale_id)

    return render(
        request,
        "nyondo/receipt_print.html",
        {"receipt": sale}
    )

# DELETE SALE
@login_required
def delete_sale(request, sale_id):
    if not request.user.is_superuser:
        messages.error(request, "Only an admin can remove a sale record.")
        return redirect("sales_list")

    sale = get_object_or_404(Sales, id=sale_id)

    if request.method == "POST":
        log_audit(
            request.user,
            "DELETE",
            f"Deleted sale {sale.receipt_no} for {sale.customer_name}",
            model_name="Sales",
            object_id=sale.pk,
        )
        sale.delete()

        messages.success(request, "Sale deleted successfully.")
        return redirect("sales_list")

    return render(
        request,
        "nyondo/delete_sales.html",
        {
            "sale": sale
        }
    )


# VOID SALE
@login_required
def void_sale(request, sale_id):
    if not request.user.is_superuser:
        messages.error(request, "Only an admin can void a sale.")
        return redirect("sales_list")

    sale = get_object_or_404(Sales.objects.select_related("product", "voided_by"), id=sale_id)

    if sale.is_voided:
        messages.info(request, f"Sale {sale.receipt_no} has already been voided.")
        return redirect("sales_list")

    if request.method == "POST":
        reason = request.POST.get("reason", "")

        try:
            sale.void(request.user, reason)
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
            return redirect("sales_list")

        log_audit(
            request.user,
            "VOID",
            f"Voided sale {sale.receipt_no} for {sale.customer_name}. Reason: {reason or 'No reason provided'}",
            model_name="Sales",
            object_id=sale.pk,
        )

        messages.success(
            request,
            f"Sale {sale.receipt_no} voided successfully and stock was returned."
        )
        return redirect("sales_list")

    return render(request, "nyondo/void_sale.html", {"sale": sale})

# LIST ALL SUPPLIER CREDITS
@login_required
def credit_list(request):

    credits = SupplierCredit.objects.select_related(
        "supplier"
    ).order_by("-date_supplied")

    context = {"credits": credits}
    return render(request, "nyondo/credit_list.html", context)
        


# LIST SUPPLIERS
@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by("name")
    return render(request, "nyondo/supplier_list.html", {"suppliers": suppliers})


# ADD SUPPLIER
@login_required
def add_supplier(request):
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            log_audit(
                request.user,
                "CREATE",
                f"Registered supplier {supplier.name}",
                model_name="Supplier",
                object_id=supplier.pk,
            )
            messages.success(request, "Supplier registered successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm()

    return render(request, "nyondo/add_supplier.html", {"form": form})


# ADD NEW CREDIT
@login_required
def add_credit(request):

    if request.method == "POST":

        form = SupplierCreditForm(request.POST)

        if form.is_valid():

            credit = form.save()
            log_audit(
                request.user,
                "CREDIT",
                f"Added supplier credit for {credit.supplier.name}: {credit.product_name} ({credit.quantity})",
                model_name="SupplierCredit",
                object_id=credit.pk,
            )

            messages.success(
                request,
                "Supplier credit added successfully."
            )

            return redirect("credit_list")
        else:
            messages.error(request, "Please fix the errors below and try again.")

    else:
        form = SupplierCreditForm()

    context = {
        "form": form
    }

    return render(
        request,
        "nyondo/add_credit.html",
        context
    )


# EDIT CREDIT
@login_required
def edit_credit(request, pk):

    credit = get_object_or_404(
        SupplierCredit,
        pk=pk
    )

    if request.method == "POST":

        form = SupplierCreditForm(
            request.POST,
            instance=credit
        )

        if form.is_valid():

            credit = form.save()
            log_audit(
                request.user,
                "CREDIT",
                f"Updated supplier credit for {credit.supplier.name}: {credit.product_name} ({credit.quantity})",
                model_name="SupplierCredit",
                object_id=credit.pk,
            )

            messages.success(
                request,
                "Supplier credit updated successfully."
            )

            return redirect("credit_list")

    else:

        form = SupplierCreditForm(
            instance=credit
        )

    context = {
        "form": form,
        "credit": credit
    }

    return render(
        request,
        "nyondo/edit_credit.html",
        context
    )

# DELETE CREDIT
@login_required
def delete_credit(request, pk):

    credit = get_object_or_404(
        SupplierCredit,
        pk=pk
    )

    if request.method == "POST":

        log_audit(
            request.user,
            "DELETE",
            f"Deleted supplier credit for {credit.supplier.name}: {credit.product_name}",
            model_name="SupplierCredit",
            object_id=credit.pk,
        )
        credit.delete()

        messages.success(
            request,
            "Supplier credit deleted successfully."
        )

        return redirect("credit_list")

    context = {
        "credit": credit
    }

    return render(
        request,
        "nyondo/delete_credit.html",
        context
    )

#deposit scheme list view

# DEPOSIT LIST
@login_required
def deposit_list(request):

    deposits = DepositScheme.objects.all().order_by("-registration_date")

    context = {
        "deposits": deposits
    }

    return render(
        request,
        "nyondo/deposit_list.html",
        context
    )


# ADD DEPOSIT
@login_required
def add_deposit(request):

    form = DepositSchemeForm(request.POST or None)

    if form.is_valid():
        deposit = form.save()
        log_audit(
            request.user,
            "DEPOSIT",
            f"Registered deposit for {deposit.customer_name}: {deposit.product_name} ({deposit.quantity})",
            model_name="DepositScheme",
            object_id=deposit.pk,
        )

        messages.success(
            request,
            "Deposit registered successfully."
        )

        return redirect("deposit_receipt_print", deposit_id=deposit.id)

    return render(
        request,
        "nyondo/add_deposit.html",
        {"form": form}
    )


@login_required
def deposit_receipt(request, deposit_id):

    deposit = get_object_or_404(DepositScheme, id=deposit_id)

    return render(
        request,
        "nyondo/deposit_receipt_details.html",
        {"deposit": deposit}
    )


@login_required
def deposit_receipt_print(request, deposit_id):

    deposit = get_object_or_404(DepositScheme, id=deposit_id)

    return render(
        request,
        "nyondo/deposit_receipt_print.html",
        {"deposit": deposit}
    )


# EDIT DEPOSIT
@login_required
def edit_deposit(request, pk):

    deposit = get_object_or_404(DepositScheme, pk=pk)

    form = DepositSchemeForm(request.POST or None, instance=deposit)

    if form.is_valid():
        deposit = form.save()
        log_audit(
            request.user,
            "DEPOSIT",
            f"Updated deposit for {deposit.customer_name}: {deposit.product_name} ({deposit.quantity})",
            model_name="DepositScheme",
            object_id=deposit.pk,
        )

        messages.success(
            request,
            "Deposit updated successfully."
        )

        return redirect("deposit_list")

    return render(
        request,
        "nyondo/edit_deposit.html",
        {
            "form": form,
            "deposit": deposit
        }
    )


# DELETE DEPOSIT
@login_required
def delete_deposit(request, pk):

    deposit = get_object_or_404(DepositScheme, pk=pk)

    if request.method == "POST":
        log_audit(
            request.user,
            "DELETE",
            f"Deleted deposit for {deposit.customer_name}: {deposit.product_name}",
            model_name="DepositScheme",
            object_id=deposit.pk,
        )
        deposit.delete()

        messages.success(
            request,
            "Deposit deleted successfully."
        )

        return redirect("deposit_list")

    return render(
        request,
        "nyondo/delete_deposit.html",
        {"deposit": deposit}
    )

# REPORTS VIEW
@login_required
def sales_report(request):
    sales = Sales.objects.select_related("product").filter(is_voided=False).order_by("-sale_date")

    # Totals calculated in Python
    total_revenue = sum(sale.final_total for sale in sales)
    total_profit = sum(sale.profit for sale in sales)
    sales_count = sales.count()

    context = {
        "sales": sales,
        "sales_count": sales_count,
        "total_sales": total_revenue,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
    }
    return render(request, "nyondo/reports/sales_report.html", context)


# STOCK REPORT
@login_required
def stock_report(request):
    stocks = Stock.objects.annotate(
        total_value=ExpressionWrapper(
            F("quantity") * F("selling_price"),
            output_field=DecimalField()
        )
    ).order_by("product_name")

    total_stock_value = stocks.aggregate(
        total=Sum("total_value")
    )["total"] or 0

    total_products = stocks.count()
    low_stock = stocks.filter(quantity__lte=10, quantity__gt=0).count()
    out_of_stock = stocks.filter(quantity=0).count()

    context = {
        "stocks": stocks,
        "total_stock_value": total_stock_value,
        "total_products": total_products,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
    }
    return render(request, "nyondo/reports/stock_reports.html", context)


# PROFIT REPORT
@login_required
def profit_report(request):
    sales = Sales.objects.select_related("product").filter(is_voided=False).order_by("-sale_date")

    total_revenue = sum((sale.quantity * sale.unit_price) + getattr(sale, "transport_charge", 0) for sale in sales)
    total_profit = sum((sale.unit_price - sale.product.buying_price) * sale.quantity for sale in sales)
    total_orders = sales.count()
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Top products by profit
    top_products = (
        Sales.objects.filter(is_voided=False).values("product__product_name")
        .annotate(
            total_profit=Sum(
                ExpressionWrapper(
                    (F("unit_price") - F("product__buying_price")) * F("quantity"),
                    output_field=DecimalField()
                )
            ),
            total_sales=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField()
                )
            ),
            total_quantity=Sum("quantity")
        )
        .order_by("-total_profit")[:10]
    )

    # Monthly profit
    monthly_profit = (
    Sales.objects.filter(is_voided=False)
    .annotate(month=TruncMonth("sale_date"))
    .values("month")
    .annotate(
        revenue=Sum(
            ExpressionWrapper(
                F("quantity") * F("unit_price"),
                output_field=DecimalField()
            )
        ),
        profit=Sum(
            ExpressionWrapper(
                (F("unit_price") - F("product__buying_price")) * F("quantity"),
                output_field=DecimalField()
            )
        ),
        orders=Count("id")
    )
    .order_by("month")
)

    context = {
        "sales": sales,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "total_orders": total_orders,
        "profit_margin": round(profit_margin, 2),
        "top_products": top_products,
        "monthly_profit": monthly_profit,
    }
    return render(request, "nyondo/reports/profit_reports.html", context)


# SUPPLIER CREDIT REPORT
@login_required
def credit_report(request):
    credits = SupplierCredit.objects.all().order_by("-id")

    total_credit = credits.aggregate(total=Sum("balance"))["total"] or 0
    pending_credits = credits.filter(status="Pending")
    cleared_credits = credits.filter(status="Cleared")

    pending_total = pending_credits.aggregate(total=Sum("balance"))["total"] or 0
    cleared_total = cleared_credits.aggregate(total=Sum("balance"))["total"] or 0

    context = {
        "credits": credits,
        "total_credit": total_credit,
        "pending_credits": pending_credits,
        "cleared_credits": cleared_credits,
        "pending_total": pending_total,
        "cleared_total": cleared_total,
    }
    return render(request, "nyondo/reports/credit_reports.html", context)


# DEPOSIT REPORT
@login_required
def deposit_report(request):
    deposits = DepositScheme.objects.all().order_by("-id")

    total_deposits = deposits.aggregate(total=Sum("amount_deposited"))["total"] or 0
    total_expected = deposits.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("unit_price") * F("quantity"),
                output_field=DecimalField()
            )
        )
    )["total"] or 0

    total_balance = total_expected - total_deposits

    completed = deposits.filter(amount_deposited__gte=F("unit_price") * F("quantity"))
    pending = deposits.filter(amount_deposited__lt=F("unit_price") * F("quantity"))

    context = {
        "deposits": deposits,
        "total_deposits": total_deposits,
        "total_expected": total_expected,
        "total_balance": total_balance,
        "completed_count": completed.count(),
        "pending_count": pending.count(),
    }
    return render(request, "nyondo/reports/deposit_reports.html", context)


# REPORTS HOME
@login_required
def reports_home(request):
    return render(request, "nyondo/reports/reports_home.html")


# AUDIT LOG VIEW
@login_required
def audit_log(request):
    logs = AuditLog.objects.select_related("user").order_by("-timestamp")
    query = request.GET.get("q")
    action = request.GET.get("action")

    if query:
        logs = logs.filter(
            Q(user__username__icontains=query) |
            Q(description__icontains=query)
        )

    if action and action in dict(AuditLog.ACTION_TYPES):
        logs = logs.filter(action=action)

    return render(request, "nyondo/audit_log.html", {
        "logs": logs,
        "query": query,
        "action": action,
    })


#         # AUDIT LOG
#         AuditLog.objects.create(
#             user=request.user,
#             action="STOCK",
#             description=f"Added stock: {stock.product_name} ({stock.quantity})"
#         )

#         return redirect("stock_dashboard")
    
# def add_sale(request):

#         # 🔥 AUDIT LOG
#         AuditLog.objects.create(
#             user=request.user,
#             action="SALE",
#             description=f"Sold {sale.quantity} of {sale.product_name} to {sale.customer_name}"
#         )

#         return redirect("sales_dashboard")

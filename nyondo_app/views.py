from urllib import request

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import DecimalField, ExpressionWrapper, Sum, F, Q, Count
from .models import *
from django.contrib.auth.models import User
from django.utils import timezone   
from .forms import StockForm, SupplierCreditForm, DepositSchemeForm
from django.db.models.functions import TruncMonth




# Create your views here.
def register_view(request):

    if request.method == "POST":

        form = UserCreationForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Account created successfully."
            )

            return redirect("register")

    else:

        form = UserCreationForm()

    users = User.objects.all().order_by("-id")

    context = {
        "form": form,
        "users": users,
    }

    return render(
        request,
        "accounts/register.html",
        context
    )
    
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

            # SAFE: define groups AFTER login
            group_names = list(
                user.groups.values_list("name", flat=True)
            )

            if user.is_superuser:
                return redirect("admin_dashboard")

            elif "Sales" in group_names:
                return redirect("sales_dashboard")

            elif "Stock" in group_names:
                return redirect("stock_dashboard")

            else:
                messages.error(
                    request,
                    f"No role assigned. Groups found: {group_names}"
                )
                return redirect("login")

        else:

            messages.error(
                request,
                "Invalid username or password"
            )

            return redirect("login")

    return render(request, "accounts/login.html")



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

            # SAFE: define groups AFTER login
            group_names = list(
                user.groups.values_list("name", flat=True)
            )

            if user.is_superuser:
                return redirect("admin_dashboard")

            elif "Sales" in group_names:
                return redirect("sales_dashboard")

            elif "Stock" in group_names:
                return redirect("stock_dashboard")

            else:
                messages.error(
                    request,
                    f"No role assigned. Groups found: {group_names}"
                )
                return redirect("login")

        else:

            messages.error(
                request,
                "Invalid username or password"
            )

            return redirect("login")

    return render(request, "accounts/login.html")    

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")


#dashboard view 


@login_required
def admin_dashboard(request):

    sales = Sales.objects.select_related("product").all()

    # =========================
    # REVENUE (DB SAFE)
    # =========================
    total_revenue = sales.aggregate(
        total=Sum(
            ExpressionWrapper(
                (F("quantity") * F("unit_price")) + 0,
                output_field=DecimalField()
            )
        )
    )["total"] or 0

    # =========================
    # PROFIT (DB SAFE - FIXED)
    # =========================
    total_profit = sales.aggregate(
        total=Sum(
            ExpressionWrapper(
                (F("unit_price") - F("product__buying_price")) * F("quantity"),
                output_field=DecimalField()
            )
        )
    )["total"] or 0

    # =========================
    # ORDERS + ITEMS
    # =========================
    total_orders = sales.count()

    total_items_sold = sales.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    # =========================
    # STOCK VALUE
    # =========================
    stock_value = Stock.objects.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("quantity") * F("selling_price"),
                output_field=DecimalField()
            )
        )
    )["total"] or 0

    total_products = Stock.objects.count()

    low_stock = Stock.objects.filter(quantity__lte=10, quantity__gt=0).count()
    out_of_stock = Stock.objects.filter(quantity=0).count()

    # =========================
    # CREDIT
    # =========================
    total_credit = SupplierCredit.objects.aggregate(
        total=Sum("balance")
    )["total"] or 0

    pending_credit = SupplierCredit.objects.filter(status="Pending").count()
    cleared_credit = SupplierCredit.objects.filter(status="Cleared").count()

    # =========================
    # DEPOSITS
    # =========================
    total_deposits = DepositScheme.objects.aggregate(
        total=Sum("amount_deposited")
    )["total"] or 0

    pending_deposits = DepositScheme.objects.filter(
        amount_deposited__lt=F("unit_price") * F("quantity")
    ).count()

    completed_deposits = DepositScheme.objects.filter(
        amount_deposited__gte=F("unit_price") * F("quantity")
    ).count()

    # =========================
    # DELIVERY LOGIC
    # =========================
    free_deliveries = Sales.objects.filter(distance_km__lte=10).count()
    charged_deliveries = Sales.objects.filter(distance_km__gt=10).count()

    # =========================
    # RECENT SALES
    # =========================
    recent_sales = sales.order_by("-sale_date")[:10]

    # =========================
    # TOP PRODUCTS
    # =========================
    top_products = sales.values(
        "product__product_name"
    ).annotate(
        total_sold=Sum("quantity")
    ).order_by("-total_sold")[:5]

    # =========================
    # PROFIT MARGIN
    # =========================
    profit_margin = (total_profit / total_revenue * 100) if total_revenue else 0

    context = {
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "profit_margin": round(profit_margin, 2),

        "total_orders": total_orders,
        "total_items_sold": total_items_sold,

        "stock_value": stock_value,
        "total_products": total_products,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,

        "total_credit": total_credit,
        "pending_credit": pending_credit,
        "cleared_credit": cleared_credit,

        "total_deposits": total_deposits,
        "pending_deposits": pending_deposits,
        "completed_deposits": completed_deposits,

        "free_deliveries": free_deliveries,
        "charged_deliveries": charged_deliveries,

        "recent_sales": recent_sales,
        "top_products": top_products,
    }

    return render(request, "nyondo/admin_dashboard.html", context)
#stock dashboard view
@login_required
def stock_dashboard(request):

    # Get all products
    stock_products = Stock.objects.all()

    # Total number of products
    total_products = Stock.objects.count()

    # Total quantity of items in stock
    total_stock_items = Stock.objects.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    # Inventory value (buying or selling value — we use selling here)
    inventory_value = Stock.objects.aggregate(
        total=Sum(F("quantity") * F("selling_price"))
    )["total"] or 0

    # Low stock items (≤ 10)
    low_stock = Stock.objects.filter(quantity__lte=10).count()

    # Out of stock items
    out_of_stock = Stock.objects.filter(quantity=0).count()

    # Future-ready profit calculation (no sales yet)
    total_profit = Stock.objects.aggregate(
        total=Sum(
            (F("selling_price") - F("buying_price")) * F("quantity")
        )
    )["total"] or 0

    # Send to template
    context = {

        "stock_products": stock_products,

        "total_products": total_products,

        "total_stock_items": total_stock_items,

        "inventory_value": inventory_value,

        "low_stock": low_stock,

        "out_of_stock": out_of_stock,

        "total_profit": total_profit,
    }

    return render(request, "nyondo/stock_dashboard.html", context)

#sales dashboard view

@login_required
def sales_dashboard(request):

    # ================= BASIC KPIs =================
    total_sales = Sales.objects.count()

    total_revenue = Sales.objects.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    total_profit = sum(
        sale.profit for sale in Sales.objects.select_related("product")
    )

    # ================= PAYMENT STATUS =================
    paid_sales = Sales.objects.filter(payment_status="Paid").count()
    pending_sales = Sales.objects.filter(payment_status="Pending").count()

    # ================= TODAY SALES =================
    today = timezone.now().date()

    today_sales = Sales.objects.filter(
        sale_date__date=today
    ).count()

    today_revenue = sum(
        sale.final_total for sale in Sales.objects.filter(
            sale_date__date=today
        )
    )

    # ================= TOP PRODUCTS =================
    top_products = (
        Sales.objects.values("product__product_name")
        .annotate(
            total_qty=Sum("quantity")
        )
        .order_by("-total_qty")[:5]
    )

    # ================= LOW STOCK ALERT =================
    low_stock = Stock.objects.filter(quantity__lte=10)

    # ================= CONTEXT =================
    context = {

        # KPIs
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_profit": total_profit,

        # Payments
        "paid_sales": paid_sales,
        "pending_sales": pending_sales,

        # Today
        "today_sales": today_sales,
        "today_revenue": today_revenue,

        # Analytics
        "top_products": top_products,
        "low_stock": low_stock,
    }

    return render(request, "nyondo/sales_dashboard.html", context)

#  STOCK LIST SECTION
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


# ================= ADD STOCK =================
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

            # Success message
            messages.success(
                request,
                f"{stock.product_name} added successfully."
            )

            # Redirect to stock list
            return redirect("stock_list")

    # Send form to template
    return render(
        request,
        "nyondo/add_stock.html",
        {"form": form}
    )

# ================= EDIT STOCK =================
@login_required
def edit_stock(request, stock_id):

    # Get stock item or 404
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

# ================= DELETE STOCK =================

@login_required
def delete_stock(request, stock_id):

    stock = get_object_or_404(Stock, id=stock_id)

    if request.method == "POST":

        name = stock.product_name
        stock.delete()

        messages.success(request, f"{name} deleted successfully")

        return redirect("stock_list")

    return render(request, "nyondo/delete_stock.html", {"stock": stock}) 



#sales list view

# ================= SALES LIST =================
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


# ================= ADD SALE =================
@login_required
def add_sale(request):

    products = Stock.objects.all()

    if request.method == "POST":

        product = get_object_or_404(
            Stock,
            id=request.POST["product"]
        )

        quantity_sold = int(request.POST["quantity"])

        # Prevent overselling
        if quantity_sold > product.quantity:
            messages.error(request, "Not enough stock available.")
            return redirect("add_sale")

        sale = Sales.objects.create(
            customer_name=request.POST["customer_name"],
            customer_phone=request.POST["customer_phone"],
            product=product,
            quantity=quantity_sold,
            unit_price=product.selling_price,
            distance_km=request.POST.get("distance_km", 0),
            payment_status=request.POST["payment_status"],
        )

        # reduce stock
        product.quantity -= quantity_sold
        product.save()

        messages.success(
            request,
            f"Sale created successfully. Receipt No: {sale.receipt_no}"
        )

        return redirect("sales_list")

    return render(request, "nyondo/add_sale.html", {"products": products})


# ================= EDIT SALE =================
@login_required
def edit_sale(request, sale_id):

    sale = get_object_or_404(Sales, id=sale_id)
    products = Stock.objects.all()

    if request.method == "POST":

        # restore old stock
        sale.product.quantity += sale.quantity
        sale.product.save()

        new_product = get_object_or_404(
            Stock,
            id=request.POST["product"]
        )

        new_quantity = int(request.POST["quantity"])

        # prevent overselling
        if new_quantity > new_product.quantity:
            messages.error(request, "Not enough stock available.")
            return redirect("edit_sale", sale_id=sale.id)

        sale.customer_name = request.POST["customer_name"]
        sale.customer_phone = request.POST["customer_phone"]
        sale.product = new_product
        sale.quantity = new_quantity
        sale.unit_price = new_product.selling_price
        sale.distance_km = request.POST.get("distance_km", 0)
        sale.payment_status = request.POST["payment_status"]

        sale.save()

        # reduce new stock
        new_product.quantity -= new_quantity
        new_product.save()

        messages.success(request, "Sale updated successfully.")
        return redirect("sales_list")

    return render(
        request,
        "nyondo/edit_sale.html",
        {
            "sale": sale,
            "products": products
        }
    )


# ================= SALE RECEIPT (VIEW) =================
@login_required
def receipts_list(request):

    receipts = Sales.objects.all().order_by("-sale_date")

    return render(
        request,
        "nyondo/receipts_list.html",
        {"receipts": receipts}
    )

@login_required
def sale_receipt(request, sale_id):

    sale = get_object_or_404(Sales, id=sale_id)

    return render(
        request,
        "nyondo/receipt.html",
        {"sale": sale}
    )

@login_required
def receipt_print(request, sale_id):

    sale = get_object_or_404(Sales, id=sale_id)

    return render(
        request,
        "nyondo/receipt_print.html",
        {"sale": sale}
    )

# ================= DELETE SALE =================
@login_required
def delete_sale(request, sale_id):

    sale = get_object_or_404(Sales, id=sale_id)

    if request.method == "POST":

        # restore stock
        sale.product.quantity += sale.quantity
        sale.product.save()

        sale.delete()

        messages.success(request, "Sale deleted successfully.")
        return redirect("sales_list")

    return render(
        request,
        "nyondo/delete_sale.html",
        {
            "sale": sale
        }
    )

# LIST ALL SUPPLIER CREDITS
@login_required
def credit_list(request):

    credits = SupplierCredit.objects.select_related(
        "supplier"
    ).order_by("-date_supplied")

    context = {"credits": credits}
    return render(request, "nyondo/credit_list.html", context)
        


# ADD NEW CREDIT
@login_required
def add_credit(request):

    if request.method == "POST":

        form = SupplierCreditForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Supplier credit added successfully."
            )

            return redirect("credit_list")

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

            form.save()

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

# ================= DEPOSIT LIST =================
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


# ================= ADD DEPOSIT =================
@login_required
def add_deposit(request):

    form = DepositSchemeForm(request.POST or None)

    if form.is_valid():
        deposit = form.save()

        messages.success(
            request,
            "Deposit registered successfully."
        )

        return redirect("deposit_list")

    return render(
        request,
        "nyondo/add_deposit.html",
        {"form": form}
    )


# ================= EDIT DEPOSIT =================
@login_required
def edit_deposit(request, pk):

    deposit = get_object_or_404(DepositScheme, pk=pk)

    form = DepositSchemeForm(request.POST or None, instance=deposit)

    if form.is_valid():
        form.save()

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


# ================= DELETE DEPOSIT =================
@login_required
def delete_deposit(request, pk):

    deposit = get_object_or_404(DepositScheme, pk=pk)

    if request.method == "POST":
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

#=========REPORTS VIEW =============
@login_required
def sales_report(request):
    sales = Sales.objects.select_related("product").order_by("-sale_date")

    # Totals calculated in Python
    total_revenue = sum((sale.quantity * sale.unit_price) + getattr(sale, "transport_charge", 0) for sale in sales)
    total_profit = sum((sale.unit_price - sale.product.buying_price) * sale.quantity for sale in sales)
    sales_count = sales.count()

    context = {
        "sales": sales,
        "sales_count": sales_count,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
    }
    return render(request, "nyondo/reports/sales_report.html", context)


# === STOCK REPORT ===
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


# === PROFIT REPORT ===
@login_required
def profit_report(request):
    sales = Sales.objects.select_related("product").order_by("-sale_date")

    total_revenue = sum((sale.quantity * sale.unit_price) + getattr(sale, "transport_charge", 0) for sale in sales)
    total_profit = sum((sale.unit_price - sale.product.buying_price) * sale.quantity for sale in sales)
    total_orders = sales.count()
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Top products by profit
    top_products = (
        Sales.objects.values("product__product_name")
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
        Sales.objects.annotate(month=TruncMonth("sale_date"))
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


# === SUPPLIER CREDIT REPORT ===
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


# === DEPOSIT REPORT ===
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


# === REPORTS HOME ===
@login_required
def reports_home(request):
    return render(request, "nyondo/reports/reports_home.html")


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
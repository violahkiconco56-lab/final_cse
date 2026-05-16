from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Sum, F
from .models import Stock, Sales, SupplierCredit
from django.contrib.auth.models import User
# from django.utils import timezone   
from .forms import StockForm



# Create your views here.
def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully.")
            return redirect("login")

    else:
        form = UserCreationForm()

    return render(request, "accounts/register.html", {"form": form})

    
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("admin_dashboard")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")


#dashboard view 

@login_required
def admin_dashboard(request):

    total_revenue = Sales.objects.aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    stock_value = Stock.objects.aggregate(
        total=Sum(F("quantity") * F("selling_price"))
    )["total"] or 0

    total_credit = SupplierCredit.objects.aggregate(
        total=Sum("balance")
    )["total"] or 0

    total_items = Stock.objects.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    total_users = User.objects.count()

    low_stock = Stock.objects.filter(quantity__lte=10).count()
    out_of_stock = Stock.objects.filter(quantity=0).count()

    context = {
        "total_revenue": total_revenue,
        "stock_value": stock_value,
        "total_credit": total_credit,
        "total_items": total_items,
        "total_users": total_users,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
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

    total_sales = Sales.objects.count()

    total_revenue = Sales.objects.aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    recent_sales = Sales.objects.order_by("-sale_date")[:10]

    top_products = Sales.objects.values("product_name").annotate(
        units_sold=Sum("quantity")
    ).order_by("-units_sold")[:5]

    context = {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_customers": Sales.objects.values("customer_name").distinct().count(),
        "transport_charges": Sales.objects.aggregate(
            total=Sum("transport_charge")
        )["total"] or 0,
        "pending_payments": Sales.objects.filter(payment_status="Pending").aggregate(
            total=Sum("total_amount")
        )["total"] or 0,
        "recent_sales": recent_sales,
        "top_products": top_products,
    }

    return render(request, "nyondo/sales_dashboard.html", context)


# ================= STOCK LIST =================
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

#         # AUDIT LOG
#         AuditLog.objects.create(
#             user=request.user,
#             action="STOCK",
#             description=f"Added stock: {stock.product_name} ({stock.quantity})"
#         )

#         return redirect("stock_dashboard")
    
# def add_sale(request):

#     if request.method == "POST":

#         sale = Sales.objects.create(
#             customer_name=request.POST["customer_name"],
#             product_name=request.POST["product_name"],
#             quantity=request.POST["quantity"],
#             unit_price=request.POST["unit_price"],
#             total_amount=request.POST["total_amount"],
#         )

#         # 🔥 AUDIT LOG
#         AuditLog.objects.create(
#             user=request.user,
#             action="SALE",
#             description=f"Sold {sale.quantity} of {sale.product_name} to {sale.customer_name}"
#         )

#         return redirect("sales_dashboard")
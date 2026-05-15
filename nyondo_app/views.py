from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Sum, F
from .models import Stock, Sales, SupplierCredit
from django.contrib.auth.models import User
# from django.utils import timezone   



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

    stock_products = Stock.objects.all()

    total_stock_items = Stock.objects.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    stock_value = Stock.objects.aggregate(
        total=Sum(F("quantity") * F("selling_price"))
    )["total"] or 0

    low_stock_products = Stock.objects.filter(quantity__lte=10)
    out_of_stock = Stock.objects.filter(quantity=0).count()

    context = {
        "total_products": Stock.objects.count(),
        "total_stock_items": total_stock_items,
        "stock_value": stock_value,
        "low_stock": low_stock_products.count(),
        "out_of_stock": out_of_stock,
        "stock_products": stock_products,
        "low_stock_products": low_stock_products,
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

# def add_stock(request):

#     if request.method == "POST":

#         stock = Stock.objects.create(
#             product_name=request.POST["product_name"],
#             quantity=request.POST["quantity"],
#             buying_price=request.POST["buying_price"],
#             selling_price=request.POST["selling_price"],
#             category=request.POST["category"],
#             supplier_name=request.POST["supplier_name"],
#         )

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
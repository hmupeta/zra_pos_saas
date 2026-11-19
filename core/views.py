from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from .models import SystemNotification, User, Company, BranchAccess
from .serializers import UserSerializer

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)
    
    # --- FIXED LOGIC STARTS HERE ---
    if not user:
        return Response({"error": "Invalid credentials"}, status=401)

    # If authenticated, get or create token
    token, _ = Token.objects.get_or_create(user=user)

    # --- BRANCH ENFORCEMENT FOR STAFF ---
    assigned_access = BranchAccess.objects.filter(user=user).first()
    assigned_branch_id = str(assigned_access.company.id) if assigned_access else None

    if user.user_type in ('CASHIER', 'MANAGER', 'ACCOUNTANT', 'FINANCE_MANAGER', 'SALES_AGENT'):
        if not assigned_branch_id:
            return Response({"error": "No branch assigned to your account. Contact your manager."}, status=403)

    # Return the successful login response
    return Response({
        "token": token.key,
        "user": {
            "id": user.id,
            "username": user.username,
            "user_type": user.user_type,
        },
        "tenant": user.tenant.name if user.tenant else None,
        "branchId": assigned_branch_id
    })
    # --- FIXED LOGIC ENDS HERE ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({"message": "Logged out"})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def branches_list(request):
    qs = BranchAccess.objects.filter(user=request.user, company__is_active=True).select_related("company")
    return Response([{
        "id": ba.company.id, 
        "name": ba.company.name, 
        "code": ba.company.branch_code, 
        "tpin": ba.company.tpin,
        "is_current": False 
    } for ba in qs])

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def switch_branch(request):
    branch_id = request.data.get("branch_id")
    try:
        branch = Company.objects.get(pk=branch_id, tenant=request.user.tenant)
    except Company.DoesNotExist:
        return Response({"error": "Branch not found"}, status=404)
        
    has_access = request.user.branch_access.filter(company=branch).exists()
    if not has_access and request.user.user_type not in ("SUPER_ADMIN", "TENANT_OWNER", "ADMIN"):
        return Response({"error": "No access to this branch"}, status=403)
        
    request.session["branch_id"] = branch.id
    return Response({"success": True, "branch_id": branch.id, "branch_name": branch.name})

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})

# --- User Management ---
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def users_list_create(request):
    if request.user.user_type != "TENANT_OWNER":
        return Response({"error": "Only Tenant Admins can manage users"}, status=403)

    if request.method == "GET":
        users = User.objects.filter(tenant=request.tenant).order_by("-date_joined")
        return Response([{
            "id": u.id, "username": u.username, "email": u.email,
            "user_type": u.user_type, "is_active": u.is_active,
        } for u in users])

    data = request.data
    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")
    role = data.get("user_type", "SALES_AGENT")

    if not username or not password:
        return Response({"error": "Username and password required"}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=email, password=password,
                tenant=request.tenant, user_type=role, employment_status="ACTIVE"
            )
            # request.branch comes from your TenantBranchMiddleware
            if hasattr(request, 'branch') and request.branch:
                BranchAccess.objects.create(user=user, company=request.branch, is_default=True)
            return Response({"success": True, "id": user.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# --- Company Settings & Branding ---
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def company_settings(request):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Only Admins can change settings"}, status=403)
    
    branch = getattr(request, 'branch', None)
    if not branch:
        return Response({"error": "No active branch. Please select a branch."}, status=400)

    if request.method == "GET":
        return Response({
            "name": branch.name,
            "tpin": branch.tpin,
            "address": branch.address,
            "phone": branch.phone,
            "email": branch.email,
            "logo_url": branch.logo.url if branch.logo else None,
        })

    # POST (Handle Multipart for Logo Upload)
    branch.name = request.data.get("name", branch.name)
    branch.tpin = request.data.get("tpin", branch.tpin)
    branch.address = request.data.get("address", branch.address)
    branch.phone = request.data.get("phone", branch.phone)
    branch.email = request.data.get("email", branch.email)

    if "logo" in request.FILES:
        branch.logo = request.FILES["logo"]

    branch.save()
    return Response({"success": True, "message": "Settings updated"})


import csv
from django.http import HttpResponse
from inventory.models import Product
from sales.models import Invoice
from customers.models import Customer

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_products(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products.csv"'
    writer = csv.writer(response)
    writer.writerow(['Barcode', 'Name', 'Category', 'Cost', 'Selling Price', 'Stock'])
    for p in Product.objects.filter(tenant=request.tenant):
        writer.writerow([p.barcode, p.name, p.category.name if p.category else '', p.unit_cost, p.selling_price, p.current_stock])
    return response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_invoices(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    writer = csv.writer(response)
    writer.writerow(['Invoice #', 'Date', 'Cashier', 'Customer', 'Total', 'Status'])
    for i in Invoice.objects.filter(tenant=request.tenant):
        writer.writerow([i.invoice_number, i.created_at.strftime("%Y-%m-%d %H:%M"), i.cashier.username, i.customer_name, i.total, i.status])
    return response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_customers(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Phone', 'Email', 'Loyalty Points', 'Total Spent', 'Credit Balance'])
    for c in Customer.objects.filter(tenant=request.tenant):
        writer.writerow([c.full_name, c.phone_number, c.email, c.loyalty_points, c.total_spent, c.account_balance])
    return response

import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_barcode_image(request, barcode_num):
    try:
        CODE128 = barcode.get_barcode_class('code128')
        my_barcode = CODE128(barcode_num, writer=ImageWriter())
        buffer = BytesIO()
        my_barcode.write(buffer)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return Response({"success": True, "image": f"data:image/png;base64,{img_str}"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def branches_manage(request):
    if request.user.user_type not in ("TENANT_OWNER", "ADMIN"):
        return Response({"error": "Only Tenant Admins can manage branches"}, status=403)

    if request.method == "GET":
        branches = Company.objects.filter(tenant=request.tenant)
        return Response([{
            "id": b.id, "name": b.name, "tpin": b.tpin, "phone": b.phone,
            "address": b.address, "is_active": b.is_active
        } for b in branches])

    # POST: Create new branch
    data = request.data
    from django.utils.text import slugify
    
    # Check plan limits
    if not request.tenant.within_plan_limits("branches"):
         return Response({"error": f"Branch limit reached for your plan"}, status=403)

    b = Company.objects.create(
        tenant=request.tenant, name=data["name"],
        branch_code=data.get("branch_code", f"00{Company.objects.filter(tenant=request.tenant).count() + 1}"),
        tpin=data.get("tpin", ""), phone=data.get("phone", ""), address=data.get("address", "")
    )
    # Automatically assign the creator to the new branch
    BranchAccess.objects.create(user=request.user, company=b)
    
    return Response({"success": True, "id": b.id})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    qs = SystemNotification.objects.filter(tenant=request.tenant).order_by("-created_at")[:20]
    unread_count = SystemNotification.objects.filter(tenant=request.tenant, is_read=False).count()
    
    return Response({
        "unread_count": unread_count,
        "notifications": [{
            "id": n.id, "title": n.title, "message": n.message,
            "type": n.notification_type, "is_read": n.is_read,
            "link": n.link, "time": n.created_at.strftime("%Y-%m-%d %H:%M")
        } for n in qs]
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notifications_read(request):
    ids = request.data.get("ids", [])
    if ids:
        SystemNotification.objects.filter(tenant=request.tenant, id__in=ids).update(is_read=True)
    else:
        SystemNotification.objects.filter(tenant=request.tenant).update(is_read=True)
    return Response({"success": True})
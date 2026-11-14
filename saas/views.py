import secrets
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from core.models import SubscriptionPlan, User, BranchAccess
from .models import SignupApplication, TenantInvite
from .serializers import SignupApplicationSerializer, TenantInviteSerializer
from .services import TenantProvisioner


def _is_platform_admin(user):
    return user.is_authenticated and user.user_type == "PLATFORM_ADMIN"


@api_view(["GET"])
@permission_classes([AllowAny])
def list_plans(request):
    """Public endpoint — available SaaS subscription plans."""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    return Response([{
        "code": p.code,
        "name": p.name,
        "description": p.description,
        "monthly_price_zmw": float(p.monthly_price_zmw),
        "yearly_price_zmw": float(p.yearly_price_zmw),
        "trial_days": p.trial_days,
        "max_branches": p.max_branches,
        "max_users": p.max_users,
    } for p in plans])


@api_view(["POST"])
@permission_classes([AllowAny])
def submit_signup(request):
    """
    Public signup form. Creates a PENDING application.
    Platform admin must approve before tenant is created.
    """
    required = ["business_name", "contact_name", "contact_email", "contact_phone"]
    for f in required:
        if not request.data.get(f):
            return Response({"error": f"{f} is required"}, status=400)

    # Reject duplicate pending applications for same email
    existing = SignupApplication.objects.filter(
        contact_email=request.data["contact_email"],
        status="PENDING",
    ).first()
    if existing:
        return Response({
            "error": "An application with this email is already pending review",
            "application_id": existing.id,
        }, status=409)

    plan_code = request.data.get("plan_code", "TRIAL")
    plan = SubscriptionPlan.objects.filter(code=plan_code, is_active=True).first()

    app = SignupApplication.objects.create(
        business_name=request.data["business_name"],
        business_type=request.data.get("business_type", ""),
        contact_name=request.data["contact_name"],
        contact_email=request.data["contact_email"],
        contact_phone=request.data["contact_phone"],
        address=request.data.get("address", ""),
        country=request.data.get("country", "Zambia"),
        tpin=request.data.get("tpin", ""),
        plan=plan,
        requested_branch_count=int(request.data.get("requested_branch_count", 1)),
        notes=request.data.get("notes", ""),
    )

    return Response({
        "success": True,
        "application_id": app.id,
        "status": app.status,
        "message": "Application submitted. You will be notified once reviewed.",
    }, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_applications(request):
    """Platform admin: view all signup applications."""
    if not _is_platform_admin(request.user):
        return Response({"error": "Platform admin only"}, status=403)
    status_filter = request.query_params.get("status")
    qs = SignupApplication.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    return Response(SignupApplicationSerializer(qs[:200], many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def application_detail(request, pk):
    if not _is_platform_admin(request.user):
        return Response({"error": "Platform admin only"}, status=403)
    try:
        app = SignupApplication.objects.get(pk=pk)
    except SignupApplication.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
    return Response(SignupApplicationSerializer(app).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_application(request, pk):
    """Platform admin: approve and auto-provision tenant."""
    if not _is_platform_admin(request.user):
        return Response({"error": "Platform admin only"}, status=403)
    try:
        app = SignupApplication.objects.get(pk=pk)
    except SignupApplication.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    try:
        result = TenantProvisioner.approve_and_provision(app, request.user)
        return Response({
            "success": True,
            "tenant_code": result["tenant_code"],
            "owner_username": result["owner_username"],
            "owner_password": result["owner_password"],
            "trial_ends_at": result["trial_ends_at"],
            "message": "Tenant provisioned. Share credentials with the customer.",
        })
    except ValueError as e:
        return Response({"error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_application(request, pk):
    if not _is_platform_admin(request.user):
        return Response({"error": "Platform admin only"}, status=403)
    try:
        app = SignupApplication.objects.get(pk=pk)
    except SignupApplication.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    app.status = "REJECTED"
    app.rejection_reason = request.data.get("reason", "")
    app.reviewed_by = request.user
    app.reviewed_at = timezone.now()
    app.save()
    return Response({"success": True, "message": "Application rejected"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_more_info(request, pk):
    if not _is_platform_admin(request.user):
        return Response({"error": "Platform admin only"}, status=403)
    try:
        app = SignupApplication.objects.get(pk=pk)
    except SignupApplication.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    app.status = "INFO_REQUIRED"
    app.additional_info_requested = request.data.get("message", "")
    app.reviewed_by = request.user
    app.reviewed_at = timezone.now()
    app.save()
    return Response({"success": True, "message": "Info request sent"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_user(request):
    """Tenant owner/admin invites a user to their tenant."""
    if not request.tenant:
        return Response({"error": "No tenant context"}, status=400)
    if request.user.user_type not in ("TENANT_OWNER", "ADMIN"):
        return Response({"error": "Insufficient permissions"}, status=403)

    email = request.data.get("email")
    if not email:
        return Response({"error": "email required"}, status=400)

    # Plan limit check
    if not request.tenant.within_plan_limits("users"):
        return Response({
            "error": f"User limit reached for plan '{request.tenant.plan.name}'",
            "plan_max": request.tenant.plan.max_users,
        }, status=403)

    company_id = request.data.get("company_id")
    company = None
    if company_id:
        from core.models import Company
        company = Company.objects.filter(pk=company_id, tenant=request.tenant).first()

    invite = TenantInvite.objects.create(
        tenant=request.tenant,
        email=email,
        full_name=request.data.get("full_name", ""),
        user_type=request.data.get("user_type", "CASHIER"),
        company=company,
        invite_token=secrets.token_urlsafe(32),
        invited_by=request.user,
        expires_at=timezone.now() + timezone.timedelta(days=7),
    )

    # In production: send email here
    return Response({
        "success": True,
        "invite_token": invite.invite_token,
        "expires_at": invite.expires_at.isoformat(),
        "message": f"Invite created for {email}. Share this token with them.",
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def accept_invite(request):
    """Accept an invite — creates the user account."""
    token = request.data.get("token")
    password = request.data.get("password")
    username = request.data.get("username")

    if not all([token, password, username]):
        return Response({"error": "token, password, username required"}, status=400)

    try:
        invite = TenantInvite.objects.get(invite_token=token)
    except TenantInvite.DoesNotExist:
        return Response({"error": "Invalid token"}, status=404)

    if not invite.is_valid():
        return Response({"error": "Invite expired or already used"}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already taken"}, status=400)

    user = User.objects.create_user(
        username=username,
        email=invite.email,
        password=password,
        tenant=invite.tenant,
        user_type=invite.user_type,
        employment_status="ACTIVE",
        invited_by=invite.invited_by,
    )

    if invite.company:
        BranchAccess.objects.create(
            user=user, company=invite.company, is_default=True,
        )

    invite.status = "ACCEPTED"
    invite.accepted_at = timezone.now()
    invite.save()

    return Response({
        "success": True,
        "username": user.username,
        "tenant": invite.tenant.name,
        "message": "Account created. You can now log in.",
    })



from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import TenantInvoice, TenantPayment
from core.models import Tenant
from .permissions import IsPlatformAdmin

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def platform_invoices(request):
    if request.method == "GET":
        qs = TenantInvoice.objects.select_related("tenant").order_by("-invoice_date")
        return Response([{
            "id": i.id, "invoice_number": i.invoice_number,
            "tenant_name": i.tenant.name, "tenant_id": i.tenant.id,
            "date": i.invoice_date.strftime("%Y-%m-%d"),
            "due_date": i.due_date.strftime("%Y-%m-%d"),
            "total": float(i.total), "amount_paid": float(i.amount_paid),
            "balance": float(i.total - i.amount_paid),
            "status": i.status
        } for i in qs])

    # POST: Create Invoice
    data = request.data
    tenant_id = data.get("tenant_id")
    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except Tenant.DoesNotExist:
        return Response({"error": "Tenant not found"}, status=404)

    import uuid
    inv_num = f"SaaS-{uuid.uuid4().hex[:6].upper()}"
    amount = Decimal(str(data.get("amount", 0)))
    
    invoice = TenantInvoice.objects.create(
        tenant=tenant, invoice_number=inv_num,
        invoice_date=date.today(), due_date=date.today() + timedelta(days=14),
        description=f"Subscription - {tenant.plan.name if tenant.plan else 'Custom'}",
        subtotal=amount, tax_amount=0, total=amount, status="SENT"
    )
    return Response({"success": True, "id": invoice.id})

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def platform_payments(request):
    if request.method == "GET":
        qs = TenantPayment.objects.select_related("tenant", "invoice").order_by("-payment_date")
        return Response([{
            "id": p.id, "tenant_name": p.tenant.name,
            "invoice_number": p.invoice.invoice_number if p.invoice else "N/A",
            "date": p.payment_date.strftime("%Y-%m-%d"),
            "amount": float(p.amount), "method": p.payment_method,
            "reference": p.reference
        } for p in qs])

    # POST: Record Payment
    data = request.data
    invoice_id = data.get("invoice_id")
    amount = Decimal(str(data.get("amount", 0)))
    
    try:
        invoice = TenantInvoice.objects.get(pk=invoice_id)
    except TenantInvoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    payment = TenantPayment.objects.create(
        tenant=invoice.tenant, invoice=invoice,
        payment_number=f"PAY-{invoice.invoice_number}-{invoice.payments.count() + 1}",
        payment_date=date.today(), amount=amount,
        payment_method=data.get("method", "BANK"),
        reference=data.get("reference", "")
    )

    # Update Invoice Status
    invoice.amount_paid += amount
    if invoice.amount_paid >= invoice.total:
        invoice.status = "PAID"
        invoice.paid_at = timezone.now()
        invoice.tenant.subscription_status = "ACTIVE"
        invoice.tenant.save()
    invoice.save()

    return Response({"success": True})



@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def platform_gateways(request):
    from .models import PlatformGatewayConfig
    
    if request.method == "GET":
        configs = PlatformGatewayConfig.objects.all()
        return Response([{
            "provider": c.provider, "is_enabled": c.is_enabled,
            "mtn_subscription_key": c.mtn_subscription_key,
            "mtn_api_user": c.mtn_api_user, "mtn_api_key": c.mtn_api_key,
            "mtn_target_env": c.mtn_target_env,
            "api_key": c.api_key, "secret_key": c.secret_key
        } for c in configs])

    data = request.data
    config, _ = PlatformGatewayConfig.objects.get_or_create(provider=data["provider"])
    config.is_enabled = data.get("is_enabled", False)
    
    if data["provider"] == "MTN":
        config.mtn_subscription_key = data.get("mtn_subscription_key", "")
        config.mtn_api_user = data.get("mtn_api_user", "")
        config.mtn_api_key = data.get("mtn_api_key", "")
        config.mtn_target_env = data.get("mtn_target_env", "sandbox")
    else:
        config.api_key = data.get("api_key", "")
        config.secret_key = data.get("secret_key", "")
        
    config.save()
    return Response({"success": True})

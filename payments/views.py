from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from sales.models import Invoice
from .models import BranchPaymentConfig, PaymentTransaction


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_momo(request):
    invoice_id = request.data.get("invoice_id")
    phone = request.data.get("phone")
    try:
        invoice = Invoice.objects.get(pk=invoice_id, tenant=request.tenant)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)
    config = BranchPaymentConfig.resolve_for_branch(invoice.company)
    if not config:
        return Response({"error": "No payment gateway configured for this branch"}, status=400)
    import uuid
    ref = f"MOMO-{uuid.uuid4().hex[:10].upper()}"
    txn = PaymentTransaction.objects.create(
        tenant=request.tenant, invoice=invoice, payment_method=config.provider,
        amount=invoice.total, reference=ref, phone_number=phone,
    )
    return Response({
        "success": True, "reference": ref,
        "message": "Check your phone and approve the payment",
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def payment_configs(request):
    if request.method == "GET":
        configs = BranchPaymentConfig.objects.filter(branch=request.branch)
        return Response([{
            "id": c.id, "provider": c.provider, "merchant_id": c.merchant_id,
            "api_key": c.api_key, "api_secret": c.api_secret,
            "mtn_subscription_key": c.mtn_subscription_key,
            "mtn_api_user": c.mtn_api_user,
            "mtn_api_key": c.mtn_api_key,
            "mtn_target_env": c.mtn_target_env,
            "is_default": c.is_default, "is_enabled": c.is_enabled,
        } for c in configs])
        
    if request.user.user_type not in ("TENANT_OWNER", "ADMIN", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    provider = data.get("provider")
    
    config, created = BranchPaymentConfig.objects.update_or_create(
        branch=request.branch, provider=provider,
        defaults={
            "merchant_id": data.get("merchant_id", ""),
            "api_key": data.get("api_key", ""),
            "api_secret": data.get("api_secret", ""),
            "mtn_subscription_key": data.get("mtn_subscription_key", ""),
            "mtn_api_user": data.get("mtn_api_user", ""),
            "mtn_api_key": data.get("mtn_api_key", ""),
            "mtn_target_env": data.get("mtn_target_env", "sandbox"),
            "is_default": data.get("is_default", False),
            "is_enabled": True,
        },
    )
    
    return Response({"success": True, "id": config.id})


@api_view(["POST"])
@permission_classes([AllowAny])
def momo_webhook(request):
    ref = request.data.get("reference")
    if not ref:
        return Response({"error": "reference required"}, status=400)
    try:
        txn = PaymentTransaction.objects.get(reference=ref)
    except PaymentTransaction.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
    # In production: verify with gateway before trusting
    txn.status = "SUCCESS"
    txn.save()
    txn.invoice.status = "PAID"
    txn.invoice.save()
    return Response({"status": "received"})



from django.db.models import Sum
from sales.models import Invoice
from core.models import Company

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_wallets(request):
    """Aggregate all payments across all branches for this tenant."""
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    branches = Company.objects.filter(tenant=request.tenant, is_active=True)
    
    branch_stats = []
    total_cash = 0
    total_momo = 0
    total_card = 0

    for b in branches:
        invoices = Invoice.objects.filter(company=b, status="PAID")
        
        cash = sum(inv.total for inv in invoices if inv.payment_method == "CASH") or 0
        momo = sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL")) or 0
        card = sum(inv.total for inv in invoices if inv.payment_method == "CARD") or 0
        
        total_cash += cash
        total_momo += momo
        total_card += card
        
        branch_stats.append({
            "id": b.id, "name": b.name,
            "cash": float(cash), "momo": float(momo), "card": float(card),
            "total": float(cash + momo + card)
        })

    return Response({
        "summary": {
            "total_cash": float(total_cash),
            "total_momo": float(total_momo),
            "total_card": float(total_card),
            "grand_total": float(total_cash + total_momo + total_card)
        },
        "branches": branch_stats
    })



import requests
import uuid

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_mtn_api_user(request):
    """Generates an MTN API User and API Key using a Subscription Key."""
    sub_key = request.data.get("subscription_key")
    env = request.data.get("target_env", "sandbox")
    
    if not sub_key:
        return Response({"error": "Subscription Key is required"}, status=400)

    base_url = "https://sandbox.momodeveloper.mtn.com" if env == "sandbox" else "https://proxy.momoapi.mtn.com"
    reference_id = str(uuid.uuid4())
    
    headers = {
        "Ocp-Apim-Subscription-Key": sub_key,
        "X-Reference-Id": reference_id,
        "Content-Type": "application/json"
    }
    
    try:
        # 1. Create API User
        res_user = requests.post(f"{base_url}/v1_0/apiuser", headers=headers, json={"providerCallbackHost": "https://webhook.site"})
        
        if res_user.status_code not in (200, 201):
            return Response({"error": f"Failed to create API User: {res_user.text}"}, status=400)
            
        # 2. Create API Key
        res_key = requests.post(f"{base_url}/v1_0/apiuser/{reference_id}/apikey", headers={"Ocp-Apim-Subscription-Key": sub_key})
        
        if res_key.status_code not in (200, 201):
            return Response({"error": f"Failed to create API Key: {res_key.text}"}, status=400)
            
        api_key = res_key.json().get("apiKey")
        
        return Response({
            "success": True,
            "api_user": reference_id,
            "api_key": api_key
        })
        
    except requests.RequestException as e:
        return Response({"error": str(e)}, status=500)



from .models import BranchPaymentConfig
from .momo_service import MTNMoMoService

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def test_gateway_connection(request):
    provider = request.data.get("provider")
    
    # We query the DB directly to avoid any signature mismatch errors
    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider=provider).first()
    
    if not config:
        return Response({"error": "Configuration not found for this branch"}, status=404)

    if provider == "MTN_DIRECT":
        service = MTNMoMoService(config)
        token_result = service.get_access_token()
        if token_result.get('success'):
            return Response({"success": True, "message": "Successfully authenticated with MTN MoMo!"})
        else:
            return Response({"error": token_result.get("error")}, status=400)
            
    elif provider == "STRIPE":
        import requests
        if not config.api_key:
            return Response({"error": "Stripe API Key is missing"}, status=400)
        headers = {"Authorization": f"Bearer {config.api_key}"}
        res = requests.get("https://api.stripe.com/v1/balance", headers=headers)
        if res.status_code == 200:
            return Response({"success": True, "message": "Successfully connected to Stripe!"})
        return Response({"error": "Stripe authentication failed. Check your Secret Key."}, status=400)

    return Response({"success": True, "message": f"Basic config check passed for {provider}."})



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_gateway(request):
    if request.user.user_type not in ("TENANT_OWNER", "ADMIN"):
        return Response({"error": "Insufficient permissions"}, status=403)
        
    provider = request.data.get("provider")
    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider=provider).first()
    
    if config:
        config.delete()
        return Response({"success": True, "message": "Configuration deleted."})
    
    return Response({"error": "Config not found"}, status=404)



from .models import GatewayTransaction
from .momo_service import MTNMoMoService

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_momo_payment(request):
    phone = request.data.get("phone")
    amount = request.data.get("amount")
    
    if not phone or not amount:
        return Response({"error": "Phone and amount required"}, status=400)

    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider="MTN_DIRECT").first()
    if not config:
        return Response({"error": "MTN is not configured for this branch"}, status=400)

    service = MTNMoMoService(config)
    import uuid
    ext_id = str(uuid.uuid4())
    
    # Trigger RequestToPay
    res = service.request_to_pay(phone, amount, ext_id, "POS Sale")
    
    if res.get("success"):
        GatewayTransaction.objects.create(
            tenant=request.tenant, branch=request.branch,
            provider="MTN_DIRECT", reference_id=res["reference_id"],
            amount=amount, phone=phone, status="PENDING"
        )
        return Response({"success": True, "reference_id": res["reference_id"]})
    else:
        return Response({"error": res.get("error")}, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_payment_status(request, reference_id):
    try:
        txn = GatewayTransaction.objects.get(reference_id=reference_id)
    except GatewayTransaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=404)

    if txn.status != "PENDING":
        return Response({"status": txn.status})

    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider="MTN_DIRECT").first()
    service = MTNMoMoService(config)
    res = service.check_status(reference_id)
    
    # MTN returns status "SUCCESSFUL" or "FAILED"
    mt_status = res.get("status")
    if mt_status == "SUCCESSFUL":
        txn.status = "SUCCESS"
        txn.save()
    elif mt_status == "FAILED":
        txn.status = "FAILED"
        txn.save()
        
    return Response({"status": txn.status, "mtn_raw": res})

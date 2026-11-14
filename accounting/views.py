from datetime import date
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Account, Journal, JournalLine

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def accounts_list(request):
    qs = Account.objects.filter(tenant=request.tenant, is_active=True)
    return Response([{
        "id": a.id, "code": a.code, "name": a.name, "type": a.account_type,
        "balance": float(a.balance()),
    } for a in qs])

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trial_balance(request):
    accounts = Account.objects.filter(tenant=request.tenant, is_active=True, is_header=False)
    rows = []
    total_dr, total_cr = Decimal("0"), Decimal("0")
    
    for a in accounts:
        bal = a.balance()
        if bal == 0:
            continue
            
        if a.normal_balance == "DEBIT":
            if bal > 0:
                total_dr += bal
                rows.append({"code": a.code, "name": a.name, "debit": float(bal), "credit": 0})
            else:
                total_cr += abs(bal)
                rows.append({"code": a.code, "name": a.name, "debit": 0, "credit": float(abs(bal))})
        else:
            if bal > 0:
                total_cr += bal
                rows.append({"code": a.code, "name": a.name, "debit": 0, "credit": float(bal)})
            else:
                total_dr += abs(bal)
                rows.append({"code": a.code, "name": a.name, "debit": float(abs(bal)), "credit": 0})

    return Response({
        "accounts": rows,
        "total_debit": float(total_dr),
        "total_credit": float(total_cr),
        "balanced": round(total_dr, 2) == round(total_cr, 2),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def balance_sheet(request):
    def sum_type(t):
        accounts = Account.objects.filter(tenant=request.tenant, account_type=t, is_header=False)
        return sum((a.balance() for a in accounts), Decimal("0"))
        
    assets = sum_type("ASSET")
    liabilities = sum_type("LIABILITY")
    equity = sum_type("EQUITY")
    revenue = sum_type("REVENUE")
    expenses = sum_type("EXPENSE")
    net_income = revenue - expenses
    
    return Response({
        "assets": float(assets),
        "liabilities": float(liabilities),
        "equity": float(equity),
        "net_income": float(net_income),
        "balanced": round(assets, 2) == round(liabilities + equity + net_income, 2),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def income_statement(request):
    def sum_type(t):
        accounts = Account.objects.filter(tenant=request.tenant, account_type=t, is_header=False)
        return sum((a.balance() for a in accounts), Decimal("0"))
        
    revenue = sum_type("REVENUE")
    expenses = sum_type("EXPENSE")
    net_income = revenue - expenses
    margin = (net_income / revenue * 100) if revenue > 0 else 0
    
    return Response({
        "revenue": float(revenue),
        "expenses": float(expenses),
        "net_income": float(net_income),
        "margin_percent": float(margin),
    })

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def journals_list(request):
    if request.method == "GET":
        qs = Journal.objects.filter(tenant=request.tenant)
        return Response([{
            "id": j.id, "journal_number": j.journal_number, "date": j.date,
            "description": j.description, "journal_type": j.journal_type,
            "total": float(j.total_debit()), "is_balanced": j.is_balanced()
        } for j in qs[:100]])
        
    # POST: Create a new manual journal
    data = request.data
    lines = data.get("lines", [])
    
    if not lines:
        return Response({"error": "Journal must have lines"}, status=400)
        
    total_dr = sum(Decimal(str(l.get("debit", 0))) for l in lines)
    total_cr = sum(Decimal(str(l.get("credit", 0))) for l in lines)
    
    if total_dr != total_cr:
        return Response({"error": "Total debits must equal total credits"}, status=400)
        
    import datetime
    j_num = f"JV-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    
    journal = Journal.objects.create(
        tenant=request.tenant, company=request.branch,
        journal_number=j_num, date=data.get("date", date.today()),
        description=data.get("description", "Manual Entry"),
        journal_type=data.get("journal_type", "GENERAL"),
        status="POSTED", created_by=request.user,
    )
    
    for line in lines:
        account = Account.objects.get(id=line["account_id"], tenant=request.tenant)
        JournalLine.objects.create(
            journal=journal, account=account,
            debit=Decimal(str(line.get("debit", 0))),
            credit=Decimal(str(line.get("credit", 0))),
            description=line.get("description", ""),
        )
        
    return Response({"success": True, "journal_id": journal.id})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def general_ledger(request, account_id):
    account = Account.objects.get(id=account_id, tenant=request.tenant)
    lines = JournalLine.objects.filter(account=account).select_related("journal").order_by("journal__date")
    
    running_bal = account.opening_balance
    entries = []
    
    for line in lines:
        if account.normal_balance == "DEBIT":
            running_bal += line.debit - line.credit
        else:
            running_bal += line.credit - line.debit
            
        entries.append({
            "date": line.journal.date.isoformat(),
            "reference": line.journal.journal_number,
            "description": line.description or line.journal.description,
            "debit": float(line.debit),
            "credit": float(line.credit),
            "balance": float(running_bal),
        })
        
    return Response({
        "account": {"code": account.code, "name": account.name, "type": account.account_type},
        "entries": entries
    })


from .models import Expense
from django.utils import timezone
import datetime

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def expenses_list(request):
    if request.method == "GET":
        qs = Expense.objects.filter(tenant=request.tenant).order_by("-date")
        return Response([{
            "id": e.id, "date": e.date.strftime("%Y-%m-%d"),
            "account": e.account.name, "amount": float(e.amount),
            "payment_method": e.payment_method, "reference": e.reference
        } for e in qs])

    # POST: Create Expense
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER", "ACCOUNTANT"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    amount = Decimal(str(data.get("amount", 0)))
    account_id = data.get("account_id")
    payment_method = data.get("payment_method", "CASH")
    ref = data.get("reference", "")

    try:
        expense_account = Account.objects.get(id=account_id, tenant=request.tenant)
    except Account.DoesNotExist:
        return Response({"error": "Invalid expense account"}, status=400)

    # Determine credit account (Cash vs Bank)
    credit_code = "1000" if payment_method == "CASH" else "1010"
    credit_account = Account.objects.filter(tenant=request.tenant, code=credit_code).first()
    
    if not credit_account:
        return Response({"error": f"Missing system account: {credit_code}"}, status=400)

    # 1. Save Expense
    expense = Expense.objects.create(
        tenant=request.tenant, company=request.branch,
        date=data.get("date", timezone.now().date()),
        account=expense_account, amount=amount,
        payment_method=payment_method, reference=ref,
        notes=data.get("notes", ""), recorded_by=request.user
    )

    # 2. Auto-Post Journal
    journal = Journal.objects.create(
        tenant=request.tenant, company=request.branch,
        journal_number=f"EXP-{expense.id}", date=expense.date,
        description=f"Expense: {expense_account.name} - {ref}",
        journal_type="GENERAL", status="POSTED", created_by=request.user
    )
    
    # Debit Expense, Credit Cash/Bank
    JournalLine.objects.create(journal=journal, account=expense_account, debit=amount, description=f"Paid {expense_account.name}")
    JournalLine.objects.create(journal=journal, account=credit_account, credit=amount, description=f"Paid via {payment_method}")

    return Response({"success": True, "id": expense.id})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def expense_accounts(request):
    # Only return accounts that are classified as EXPENSE
    accounts = Account.objects.filter(tenant=request.tenant, account_type="EXPENSE", is_header=False)
    return Response([{"id": a.id, "name": a.name, "code": a.code} for a in accounts])

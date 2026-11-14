from rest_framework.decorators import parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import F
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product, Category, TaxRate, StockMovement
from .serializers import ProductSerializer, CategorySerializer, TaxRateSerializer
from decimal import Decimal
import uuid

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from decimal import Decimal
import uuid
from .models import Product, Category, TaxRate, StockMovement

@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def products_list(request):
    if request.method == 'GET':
        product_id = request.query_params.get('id')
        if product_id:
            try:
                p = Product.objects.get(id=product_id, tenant=request.tenant)
                return Response({
                    "id": p.id, "barcode": p.barcode, "name": p.name,
                    "category_id": p.category_id, "tax_rate_id": p.tax_rate_id,
                    "unit_cost": float(p.unit_cost), "selling_price": float(p.selling_price),
                    "discount_percentage": float(p.discount_percentage),
                    "current_stock": float(p.current_stock), "reorder_level": float(p.reorder_level),
                    "image_url": p.image.url if getattr(p, "image", None) else None,
                })
            except Product.DoesNotExist:
                return Response({"error": "Product not found"}, status=404)

        search = request.query_params.get('search', '')
        products = Product.objects.filter(tenant=request.tenant, company=request.branch, is_active=True)
        if search:
            products = products.filter(name__icontains=search) | products.filter(barcode__icontains=search)
            
        data = []
        for p in products:
            data.append({
                "id": p.id,
                "barcode": p.barcode,
                "name": p.name,
                "selling_price": float(p.selling_price),
                "discount_percentage": float(p.discount_percentage),
                "unit_cost": float(p.unit_cost),
                "current_stock": float(p.current_stock),
                "tax_rate": float(p.tax_rate.rate),
                "category_name": p.category.name,
                "image_url": p.image.url if getattr(p, "image", None) else None,
            })
        return Response(data)
        
    elif request.method == 'PUT':
        data = request.data
        product_id = data.get("id")
        if not product_id:
             return Response({"error": "Product ID required"}, status=400)
             
        try:
            p = Product.objects.get(id=product_id, tenant=request.tenant)
            p.name = data.get("name", p.name)
            p.barcode = data.get("barcode", p.barcode)
            p.category_id = data.get("category_id", p.category_id)
            p.tax_rate_id = data.get("tax_rate_id", p.tax_rate_id)
            p.unit_cost = Decimal(str(data.get("unit_cost", p.unit_cost)))
            p.selling_price = Decimal(str(data.get("selling_price", p.selling_price)))
            p.discount_percentage = Decimal(str(data.get("discount_percentage", p.discount_percentage)))
            p.reorder_level = Decimal(str(data.get("reorder_level", p.reorder_level)))
            
            # Handle Image Upload
            if "image" in request.FILES:
                p.image = request.FILES["image"]
            elif "image" in request.data and hasattr(request.data["image"], "read"):
                p.image = request.data["image"]
                
            p.save()
            
            # Return safe response (no image.url access here to avoid InMemoryUploadedFile crash)
            return Response({"success": True, "id": p.id, "has_image": bool(p.image)})
            
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
             return Response({"error": str(e)}, status=400)

    # POST: Create Product
    data = request.data
    try:
        barcode = data.get("barcode") or str(uuid.uuid4().hex[:10]).upper()
        
        product = Product.objects.create(
            tenant=request.tenant,
            company=request.branch,
            barcode=barcode,
            name=data.get("name"),
            description=data.get("description", ""),
            category_id=data.get("category_id"),
            tax_rate_id=data.get("tax_rate_id"),
            unit_cost=Decimal(str(data.get("unit_cost", 0))),
            selling_price=Decimal(str(data.get("selling_price", 0))),
            discount_percentage=Decimal(str(data.get("discount_percentage", 0))),
            current_stock=Decimal(str(data.get("current_stock", 0))),
            reorder_level=Decimal(str(data.get("reorder_level", 10))),
            zra_item_code=data.get("zra_item_code", ""),
            image=request.FILES.get("image")
        )
        return Response({"success": True, "id": product.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    # POST: Create Product
    data = request.data
    try:
        barcode = data.get("barcode") or str(uuid.uuid4().hex[:10]).upper()
        
        product = Product.objects.create(
            tenant=request.tenant,
            company=request.branch,
            barcode=barcode,
            name=data.get("name"),
            description=data.get("description", ""),
            category_id=data.get("category_id"),
            tax_rate_id=data.get("tax_rate_id"),
            unit_cost=Decimal(str(data.get("unit_cost", 0))),
            selling_price=Decimal(str(data.get("selling_price", 0))),
            discount_percentage=Decimal(str(data.get("discount_percentage", 0))),
            current_stock=Decimal(str(data.get("current_stock", 0))),
            reorder_level=Decimal(str(data.get("reorder_level", 10))),
            zra_item_code=data.get("zra_item_code", ""),
            image=request.FILES.get("image")
        )
        return Response({"success": True, "id": product.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    # POST: Create Product
    data = request.data
    try:
        barcode = data.get("barcode") or str(uuid.uuid4().hex[:10]).upper()
        
        product = Product.objects.create(
            tenant=request.tenant,
            company=request.branch,
            barcode=barcode,
            name=data.get("name"),
            description=data.get("description", ""),
            category_id=data.get("category_id"),
            tax_rate_id=data.get("tax_rate_id"),
            unit_cost=Decimal(str(data.get("unit_cost", 0))),
            selling_price=Decimal(str(data.get("selling_price", 0))),
            discount_percentage=Decimal(str(data.get("discount_percentage", 0))),
            current_stock=Decimal(str(data.get("current_stock", 0))),
            reorder_level=Decimal(str(data.get("reorder_level", 10))),
            zra_item_code=data.get("zra_item_code", ""),
            image=request.FILES.get("image")
        )
        return Response({"success": True, "id": product.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def receive_stock(request):
    """Adds inventory to an existing product."""
    try:
        product_id = request.data.get("product_id")
        qty = Decimal(str(request.data.get("quantity", 0)))
        new_cost = Decimal(str(request.data.get("unit_cost", 0)))
        supplier_ref = request.data.get("reference", "")

        product = Product.objects.get(pk=product_id, tenant=request.tenant)

        # Update stock and cost
        product.current_stock += qty
        if new_cost > 0:
            product.unit_cost = new_cost
        product.save()

        # Record the movement
        StockMovement.objects.create(
            product=product,
            quantity=qty,
            movement_type='IN',
            reference=supplier_ref,
            created_by=request.user
        )

        return Response({"success": True, "new_stock": float(product.current_stock)})
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_by_barcode(request, barcode):
    try:
        product = Product.objects.get(barcode=barcode, tenant=request.tenant, is_active=True)
        return Response(ProductSerializer(product).data)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

@api_view(["GET", "POST", "PUT"])
@permission_classes([IsAuthenticated])
def categories_list(request):
    if request.method == "GET":
        cats = Category.objects.filter(tenant=request.tenant)
        return Response([{
            "id": c.id, "name": c.name, "zra_item_code": c.zra_item_code, "is_active": c.is_active
        } for c in cats])
        
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    
    if request.method == "POST":
        c = Category.objects.create(
            tenant=request.tenant, name=data["name"], 
            zra_item_code=data.get("zra_item_code", "")
        )
        return Response({"success": True, "id": c.id}, status=201)
        
    elif request.method == "PUT":
        try:
            c = Category.objects.get(id=data["id"], tenant=request.tenant)
            c.name = data.get("name", c.name)
            c.zra_item_code = data.get("zra_item_code", c.zra_item_code)
            c.is_active = data.get("is_active", c.is_active)
            c.save()
            return Response({"success": True})
        except Category.DoesNotExist:
            return Response({"error": "Not found"}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tax_rates_list(request):
    taxes = TaxRate.objects.filter(tenant=request.tenant)
    return Response([{"id": t.id, "name": t.name, "rate": float(t.rate)} for t in taxes])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_stock_products(request):
    products = Product.objects.filter(tenant=request.tenant, current_stock__lte=F('reorder_level'), is_active=True)
    return Response(ProductSerializer(products, many=True).data)


from .models import StockTake, StockTakeItem
from accounting.models import Account, Journal, JournalLine
from django.utils import timezone
import datetime

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def stocktakes_list(request):
    if request.method == "GET":
        qs = StockTake.objects.filter(tenant=request.tenant).order_by("-created_at")
        return Response([{
            "id": s.id, "reference": s.reference, "status": s.status,
            "counted_by": s.counted_by.username, "approved_by": s.approved_by.username if s.approved_by else None,
            "date": s.created_at.strftime("%Y-%m-%d %H:%M"),
            "items_count": s.items.count()
        } for s in qs])

    # POST: Create new
    ref = f"ST-{datetime.datetime.now().strftime('%y%m%d%H%M')}"
    st = StockTake.objects.create(
        tenant=request.tenant, company=request.branch,
        reference=ref, counted_by=request.user
    )
    return Response({"success": True, "id": st.id, "reference": ref})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stocktake_detail(request, pk):
    try:
        st = StockTake.objects.get(pk=pk, tenant=request.tenant)
    except StockTake.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
    
    items = st.items.all().select_related("product")
    return Response({
        "id": st.id, "reference": st.reference, "status": st.status,
        "items": [{
            "id": i.id, "barcode": i.product.barcode, "name": i.product.name,
            "system_qty": float(i.system_qty), "counted_qty": float(i.counted_qty), "variance": float(i.variance)
        } for i in items]
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stocktake_scan(request, pk):
    """Add or update an item in the stocktake by barcode."""
    barcode = request.data.get("barcode")
    counted_qty = request.data.get("counted_qty")
    
    try:
        st = StockTake.objects.get(pk=pk, tenant=request.tenant, status="DRAFT")
        product = Product.objects.get(barcode=barcode, tenant=request.tenant)
        
        # Update if exists, else create
        item, created = StockTakeItem.objects.get_or_create(
            stocktake=st, product=product,
            defaults={"system_qty": product.current_stock, "counted_qty": counted_qty}
        )
        if not created:
            item.counted_qty = counted_qty
            item.save()
            
        return Response({"success": True, "name": product.name, "variance": float(item.variance)})
    except Product.DoesNotExist:
        return Response({"error": "Barcode not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stocktake_submit(request, pk):
    st = StockTake.objects.get(pk=pk, tenant=request.tenant)
    if not st.items.exists():
        return Response({"error": "Cannot submit empty count"}, status=400)
    st.status = "PENDING"
    st.save()
    return Response({"success": True})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stocktake_approve(request, pk):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Only Managers can approve stock counts"}, status=403)
        
    try:
        st = StockTake.objects.get(pk=pk, tenant=request.tenant, status="PENDING")
    except StockTake.DoesNotExist:
        return Response({"error": "Invalid or already approved"}, status=400)

    # 1. Update Stock and Record Movements
    for item in st.items.all():
        diff = item.counted_qty - item.system_qty
        if diff != 0:
            product = item.product
            product.current_stock = item.counted_qty
            product.save()
            
            StockMovement.objects.create(
                product=product, quantity=diff, movement_type="ADJUST",
                reference=st.reference, notes="Stocktake Adjustment", created_by=request.user
            )

    # 2. Accounting Journal for the Total Variance Value
    total_variance_value = sum((item.variance * item.product.unit_cost for item in st.items.all()))
    
    if total_variance_value != 0:
        inv_account = Account.objects.filter(tenant=request.tenant, code="1200").first() # Inventory
        shrink_account = Account.objects.filter(tenant=request.tenant, code="5900").first() # Shrinkage/Misc
        
        if inv_account and shrink_account:
            journal = Journal.objects.create(
                tenant=request.tenant, company=request.company,
                journal_number=f"JV-{st.reference}", date=timezone.now().date(),
                description=f"Stocktake Variance {st.reference}", journal_type="ADJUSTMENT",
                status="POSTED", created_by=request.user
            )
            
            if total_variance_value < 0:
                # Shrinkage (Loss)
                JournalLine.objects.create(journal=journal, account=shrink_account, debit=abs(total_variance_value))
                JournalLine.objects.create(journal=journal, account=inv_account, credit=abs(total_variance_value))
            else:
                # Overage (Gain)
                JournalLine.objects.create(journal=journal, account=inv_account, debit=total_variance_value)
                JournalLine.objects.create(journal=journal, account=shrink_account, credit=total_variance_value)

    st.status = "COMPLETED"
    st.approved_by = request.user
    st.completed_at = timezone.now()
    st.save()
    
    return Response({"success": True})



from .models import StockTransfer, StockTransferItem
from core.models import Company

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def transfers_list(request):
    if request.method == "GET":
        qs = StockTransfer.objects.filter(tenant=request.tenant).order_by("-created_at")
        return Response([{
            "id": t.id, "transfer_number": t.transfer_number,
            "from_branch": t.from_company.name, "to_branch": t.to_company.name,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "status": t.status
        } for t in qs])

    # POST: Create Transfer
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    from_id = data.get("from_company_id")
    to_id = data.get("to_company_id")
    items = data.get("items", [])

    if from_id == to_id:
        return Response({"error": "Source and destination cannot be the same"}, status=400)
    if not items:
        return Response({"error": "No items selected"}, status=400)

    import datetime
    ref = f"TRF-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    transfer = StockTransfer.objects.create(
        tenant=request.tenant, transfer_number=ref,
        from_company_id=from_id, to_company_id=to_id,
        created_by=request.user
    )

    for item in items:
        # 1. Deduct from Source Branch
        try:
            source_prod = Product.objects.get(id=item["product_id"], company_id=from_id)
            qty = Decimal(str(item["quantity"]))
            
            if source_prod.current_stock < qty:
                transfer.delete() # Rollback
                return Response({"error": f"Not enough stock for {source_prod.name}"}, status=400)
                
            source_prod.current_stock -= qty
            source_prod.save()
        except Product.DoesNotExist:
            transfer.delete()
            return Response({"error": "Source product not found"}, status=404)

        # 2. Add to Destination Branch
        # We match the product in the destination branch by barcode
        dest_prod, created = Product.objects.get_or_create(
            tenant=request.tenant, company_id=to_id, barcode=source_prod.barcode,
            defaults={
                "name": source_prod.name, "category": source_prod.category,
                "tax_rate": source_prod.tax_rate, "unit_cost": source_prod.unit_cost,
                "selling_price": source_prod.selling_price, "zra_item_code": source_prod.zra_item_code
            }
        )
        dest_prod.current_stock += qty
        dest_prod.save()

        # 3. Record Transfer Item
        StockTransferItem.objects.create(
            transfer=transfer, product=source_prod, quantity=qty
        )

    return Response({"success": True, "transfer_number": ref})



import csv
from django.http import HttpResponse
from decimal import Decimal, InvalidOperation

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_product_template(request):
    """Generates a blank CSV template for importing products."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="product_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Barcode', 'Product Name', 'Category', 'Cost Price', 'Selling Price', 'Opening Stock', 'Tax Rate'])
    writer.writerow(['8901234567890', 'Coca-Cola 500ml', 'Beverages', '5.60', '8.00', '100', '16'])
    writer.writerow(['8901234567891', 'Bread Loaf', 'Food', '11.00', '15.00', '50', '16'])
    return response

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_products_csv(request):
    """Parses an uploaded CSV and creates products."""
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    csv_file = request.FILES.get("file")
    if not csv_file:
        return Response({"error": "No file uploaded"}, status=400)

    if not csv_file.name.endswith('.csv'):
        return Response({"error": "File must be a CSV"}, status=400)

    try:
        decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)
        
        created_count = 0
        errors = []

        # Get default Tax Rate (e.g., 16%) as fallback
        default_tax = TaxRate.objects.filter(tenant=request.tenant, rate=16).first()

        for row_num, row in enumerate(reader, start=2):
            try:
                barcode = row.get('Barcode', '').strip()
                name = row.get('Product Name', '').strip()
                category_name = row.get('Category', 'Uncategorized').strip()
                cost = Decimal(row.get('Cost Price', '0').strip() or '0')
                price = Decimal(row.get('Selling Price', '0').strip() or '0')
                stock = Decimal(row.get('Opening Stock', '0').strip() or '0')
                tax_rate_val = row.get('Tax Rate', '').strip()

                if not barcode or not name:
                    errors.append(f"Row {row_num}: Missing Barcode or Name")
                    continue

                # 1. Handle Category
                category, _ = Category.objects.get_or_create(
                    tenant=request.tenant, name=category_name,
                    defaults={"zra_item_code": "5059690800"}
                )

                # 2. Handle Tax Rate
                tax_rate = default_tax
                if tax_rate_val:
                    try:
                        tax_rate = TaxRate.objects.filter(tenant=request.tenant, rate=Decimal(tax_rate_val)).first() or default_tax
                    except InvalidOperation:
                        pass
                
                if not tax_rate:
                    errors.append(f"Row {row_num}: No valid Tax Rate found.")
                    continue

                # 3. Create Product
                _, created = Product.objects.update_or_create(
                    tenant=request.tenant, company=request.branch, barcode=barcode,
                    defaults={
                        "name": name,
                        "category": category,
                        "tax_rate": tax_rate,
                        "unit_cost": cost,
                        "selling_price": price,
                        "current_stock": stock,
                        "zra_item_code": category.zra_item_code,
                        "is_active": True
                    }
                )
                if created:
                    created_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        return Response({
            "success": True, 
            "created": created_count, 
            "errors": errors[:10] # Return first 10 errors to avoid huge payloads
        })

    except Exception as e:
        return Response({"error": f"Failed to read file: {str(e)}"}, status=400)

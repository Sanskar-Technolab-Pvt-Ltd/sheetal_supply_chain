import frappe
from frappe import _
from erpnext.stock.utils import get_stock_balance
from frappe.utils import nowdate, nowtime, flt


# ! Fetch latest FAT and SNF values from Quality Inspection and calculate FAT/SNF KG for real-time client-side updates
@frappe.whitelist()
def update_fat_snf_js(qi, stock_qty=None):
    """Always return fresh FAT/SNF from latest QI, even if previous QI was cancelled."""
    if not qi:
        return {"fat": 0, "snf": 0, "fat_kg": 0, "snf_kg": 0}
    # Always load fresh QI from database (NO CACHE)
    qi_doc = frappe.get_doc("Quality Inspection", qi)
    # Force load fresh child table rows
    readings = frappe.get_all(
        "Quality Inspection Reading",
        filters={"parent": qi},
        fields=["specification", "reading_1"],
        order_by="idx asc",
    )
    fat = 0
    snf = 0
    # Fresh, newly created QI reading will be picked here
    for r in readings:
        spec = (r.specification or "").strip().upper()
        if spec == "FAT":
            fat = frappe.utils.flt(r.reading_1 or 0)
        if spec in ("S.N.F.", "SNF", "S N F"):
            snf = frappe.utils.flt(r.reading_1 or 0)
    stock_qty = frappe.utils.flt(stock_qty or 0)
    return {
        "fat": fat,
        "snf": snf,
        "fat_kg": (fat/100) * stock_qty,
        "snf_kg": (snf/100) * stock_qty
    }
 
 
# ! Update FAT, SNF, and their KG values on Purchase Receipt items before save based on linked Quality Inspection
def validate_purchase_receipt(doc, method):
    """Update FAT/SNF values before saving if QI has changed"""
    for item in doc.items:
        if item.quality_inspection:
            # Get fresh values from QI
            values = update_fat_snf_js(item.quality_inspection, item.stock_qty)
            # Update item fields
            item.custom_fat = values["fat"]
            item.custom_snf = values["snf"]
            item.custom_fat_kg = values["fat_kg"]
            item.custom_snf_kg = values["snf_kg"]
        else:
            # Clear values if no QI
            item.custom_fat = 0
            item.custom_snf = 0
            item.custom_fat_kg = 0
            item.custom_snf_kg = 0


# ! Create Milk Quality Ledger Entries (MQLE) on Purchase Receipt submit for milk-type items using post-transaction stock balance
def create_mqle_on_pr_submit(doc, method=None):
    """
    Create Milk Quality Ledger Entry (MQLE) on Purchase Receipt Submit.
    Only for PR Item rows where custom_maintain_fat_snf = 1.
    """
    posting_date = doc.posting_date or nowdate()
    posting_time = doc.posting_time or nowtime()

    for row in doc.items:

        # Only process milk items
        if not row.custom_maintain_fat_snf:
            continue
        

        # -------------------------------
        # Get balance AFTER transaction
        # -------------------------------
        stock_qty_after = get_stock_balance(
            item_code=row.item_code,
            warehouse=row.warehouse,
            posting_date=posting_date,
            posting_time=posting_time,
            with_valuation_rate=False,
            with_serial_no=False
        )
        
                # -------------------------------
        #  UOM handling (same as QI)
        # -------------------------------
        stock_uom = frappe.get_cached_value("Item", row.item_code, "stock_uom") or "KG"
        included_uom = "Litre"

        conversion_factor = frappe.db.get_value(
            "UOM Conversion Detail",
            {"parent": row.item_code, "uom": included_uom},
            "conversion_factor"
        ) or 1.0

        qty_after_litre = (
            stock_qty_after / conversion_factor
            if stock_uom != included_uom
            else stock_qty_after
        )

        mqle = frappe.new_doc("Milk Quality Ledger Entry")

        # Basic Details
        mqle.item_code = row.item_code
        mqle.item_name = row.item_name
        mqle.warehouse = row.warehouse
        mqle.serial_no = row.serial_no
        mqle.batch_no = row.batch_no

        mqle.voucher_type = doc.doctype     
        mqle.voucher_no = doc.name           
        mqle.voucher_detail_no = row.name    

        mqle.posting_date = doc.posting_date
        mqle.posting_time = doc.posting_time

        # Transaction Details
        # mqle.actual_quantity = row.stock_qty       
        mqle.stock_uom = row.stock_uom
        mqle.uom = row.uom

        # Milk Parameters
        mqle.fat_per = row.custom_fat
        mqle.snf_per = row.custom_snf

        mqle.fat = row.custom_fat_kg
        mqle.snf = row.custom_snf_kg

        mqle.qty_in_liter = row.qty
        mqle.qty_in_kg = row.stock_qty
        
        mqle.qty_after_transaction_in_liter = qty_after_litre
        mqle.qty_after_transaction_in_kg = stock_qty_after
        

        # Save + Submit
        mqle.save(ignore_permissions=True)
        mqle.submit()




# ! Cancel all Milk Quality Ledger Entries linked to a Purchase Receipt when the Purchase Receipt is cancelled
def cancel_mqle_on_pr_cancel(doc, method=None):
    """
    Cancel all MQLE entries created from this Purchase Receipt
    when PR is cancelled.
    """
    
    # Find MQLE linked to this PR
    mqle_list = frappe.get_all(
        "Milk Quality Ledger Entry",
        filters={
            "voucher_type": doc.doctype,   
            "voucher_no": doc.name         
        },
        fields=["name", "docstatus"]
    )

    if not mqle_list:
        return  # No linked MQLE exists

    for mqle in mqle_list:
        if mqle.docstatus == 1: 
            mqle_doc = frappe.get_doc("Milk Quality Ledger Entry", mqle.name)
            mqle_doc.is_cancelled = 1
            mqle_doc.cancel()



# ! Validate milk type on Purchase Receipt items against Supplier Milk Profile configuration
def validate_milk_type_with_supplier_profile(doc, method=None):
    if not doc.supplier:
        return

    # Check if PR has any milk-type items (based on milk type, not checkbox)
    has_milk_items = any(
        getattr(item, "custom_milk_type", None)
        for item in doc.items
    )
    # If no milk items → no validation needed
    if not has_milk_items:
        return

    # Fetch allowed milk types from Supplier → custom_supplier_milk_profile
    supplier_milk_types = frappe.db.get_all(
        "Supplier Milk Profile",
        filters={"parent": doc.supplier},
        fields=["milk_type"],
        pluck="milk_type"
    )

    # Supplier has NO milk types but PR has milk items
    if not supplier_milk_types:
        frappe.throw(
            f"Supplier <b>{doc.supplier}</b> has no Milk Types configured.<br>"
            f"Please set Milk Types in <b>Supplier</b> before creating this Purchase Receipt."
        )

    # Validate each milk item
    for item in doc.items:
        if not getattr(item, "custom_maintain_fat_snf", 0):
            continue

        milk_type = item.custom_milk_type

        if not milk_type:
            frappe.throw(
                f"Milk Type is required for milk item <b>{item.item_code}</b> (Row {item.idx})."
            )

        if milk_type not in supplier_milk_types:
            frappe.throw(
                f"Milk Type <b>{milk_type}</b> in row {item.idx} is not allowed for Supplier <b>{doc.supplier}</b>.<br>"
                f"Allowed Milk Types: <b>{', '.join(supplier_milk_types)}</b>"
            )





# Cow-buffalo rate logic 

# ! Fetch supplier-specific milk pricing profile for a given milk type including baseline FAT, SNF, and base rate
def get_supplier_milk_profile(supplier: str, custom_milk_type: str):
    if not supplier or not custom_milk_type:
        return {}

    profile = frappe.db.get_value(
        "Supplier Milk Profile",
        {
            "parent": supplier,
            "milk_type": custom_milk_type,
            "is_default": 1,
        },
        ["baseline_fat", "baseline_snf", "base_rate"],
        as_dict=True,
    )
    return profile or {}

# ! Calculate SNF percentage based on FAT percentage and Lactometer Reading (LR)
def calculate_snf(fat: float, lr: float) -> float:
    fat = flt(fat)
    lr = flt(lr)
    return (fat / 4.0) + (0.2 * lr) + 0.14

# ! Fetch Milk Type configuration document (Cow, Buffalo, etc.) required for rate calculation
def get_milk_type_config(milk_type: str):
    """Fetch Milk Type doc (Cow / Buffalo etc.)."""
    if not milk_type:
        frappe.throw("Milk Type is required to calculate rate.")
    return frappe.get_doc("Milk Type", milk_type)

# ! Calculate milk purchase rate and amount for a Purchase Receipt item based on FAT, SNF, milk type, and supplier rules
@frappe.whitelist()
def get_milk_rate_for_pr_item(
    supplier: str,
    custom_milk_type: str,
    custom_fat: float,
    custom_snf: float,
    weight_kg: float,
):
    custom_fat = flt(custom_fat)
    custom_snf = flt(custom_snf)
    weight_kg = flt(weight_kg)

    if not supplier:
        frappe.throw("Supplier is required to calculate milk rate.")
    if not custom_milk_type:
        frappe.throw("Milk Type is required to calculate milk rate.")
    if not weight_kg:
        frappe.throw("Weight (KG) is required to calculate milk rate.")
    if not custom_fat:
        frappe.throw("FAT % is required to calculate milk rate.")
    if not custom_snf:
        frappe.throw("SNF is required to calculate milk rate.")

    mt = get_milk_type_config(custom_milk_type)
    profile = get_supplier_milk_profile(supplier, custom_milk_type)

    kg_per_litre = 1.0339
    qty_litre = weight_kg / kg_per_litre if kg_per_litre else 0

    baseline_fat = flt(profile.get("baseline_fat") or 0)
    baseline_snf = flt(profile.get("baseline_snf") or 0)

    base_rate = flt(profile.get("base_rate") or 0)
    if not base_rate:
        frappe.throw(f"Base Rate not defined for Supplier {supplier} & Milk Type {custom_milk_type}")

    fat_addition = 0.0
    fat_deduction = 0.0
    snf_addition = 0.0
    snf_deduction = 0.0

    snf_addition_rate = flt(getattr(mt, "snf_addition", 0))
    snf_deduction_rate = flt(getattr(mt, "snf_deduction", 0))
    fat_addition_rate = flt(getattr(mt, "fat_addition", 0))
    fat_deduction_rate = flt(getattr(mt, "fat_deduction", 0))

    if mt.base_rate_type == "Per Litre":
        if baseline_fat:
            fat_diff = custom_fat - baseline_fat

            if getattr(mt, "fat_addition_enabled", 0) and fat_diff > 0:
                fat_addition = fat_diff * fat_addition_rate

            if getattr(mt, "fat_deduction_enabled", 0) and fat_diff < 0:
                fat_deduction = abs(fat_diff) * fat_deduction_rate

        if baseline_snf:
            snf_diff = custom_snf - baseline_snf

            if getattr(mt, "snf_addition_enabled", 0) and snf_diff > 0:
                snf_addition = snf_diff * snf_addition_rate

            if getattr(mt, "snf_deduction_enabled", 0) and snf_diff < 0:
                snf_deduction = abs(snf_diff) * snf_deduction_rate

        final_rate = base_rate + fat_addition + snf_addition - fat_deduction - snf_deduction
        amount = final_rate * qty_litre

        return {
            "custom_snf": custom_snf,
            "qty_litre": qty_litre,
            "kg_per_litre": kg_per_litre,
            "final_rate": final_rate,
            "amount": amount,
            "base_rate": base_rate,
            "fat_addition": fat_addition,
            "fat_deduction": fat_deduction,
            "snf_addition": snf_addition,
            "snf_deduction": snf_deduction,
            "rate_type": "Per Litre",
            "payable_fat_kg": 0,
            "rate_per_litre_display": final_rate,
        }

    elif mt.base_rate_type == "Per KG Fat":
        if baseline_fat:
            fat_diff = custom_fat - baseline_fat

            if getattr(mt, "fat_addition_enabled", 0) and fat_diff > 0:
                fat_addition = fat_diff * fat_addition_rate

            if getattr(mt, "fat_deduction_enabled", 0) and fat_diff < 0:
                fat_deduction = abs(fat_diff) * fat_deduction_rate

        if baseline_snf:
            snf_diff = custom_snf - baseline_snf

            if getattr(mt, "snf_addition_enabled", 0) and snf_diff > 0:
                snf_addition = snf_diff * snf_addition_rate

            if getattr(mt, "snf_deduction_enabled", 0) and snf_diff < 0:
                snf_deduction = abs(snf_diff) * snf_deduction_rate

        final_rate_per_kg_fat = base_rate + fat_addition + snf_addition - fat_deduction - snf_deduction

        payable_fat_kg = (custom_fat / 100.0) * weight_kg

        amount = payable_fat_kg * final_rate_per_kg_fat

        rate_per_litre_display = amount / qty_litre if qty_litre else 0

        return {
            "custom_snf": custom_snf,
            "qty_litre": qty_litre,
            "kg_per_litre": kg_per_litre,
            "final_rate": final_rate_per_kg_fat,
            "amount": amount,
            "base_rate": base_rate,
            "fat_addition": fat_addition,
            "fat_deduction": fat_deduction,
            "snf_addition": snf_addition,
            "snf_deduction": snf_deduction,
            "rate_type": "Per KG Fat",
            "payable_fat_kg": payable_fat_kg,
            "rate_per_litre_display": rate_per_litre_display,
        }

    else:
        frappe.throw(f"Unsupported Base Rate Type {mt.base_rate_type} for Milk Type {custom_milk_type}")

# ! Set milk pricing fields, rates, and amounts on Purchase Receipt items based on calculated milk rate logic
def set_milk_pricing_on_items(doc, method=None):
    if doc.doctype != "Purchase Receipt":
        return
    if not getattr(doc, "supplier", None):
        return

    for item in doc.items:
        if not getattr(item, "custom_milk_type", None):
            continue
        
        if not (
            getattr(item, "custom_fat", None)
            and getattr(item, "custom_snf", None)
        ):
            continue

        weight_kg = flt(getattr(doc, "custom_net_weight", 0))
        if not weight_kg:
            weight_kg = flt(item.qty or 0)

        res = get_milk_rate_for_pr_item(
            supplier=doc.supplier,
            custom_milk_type=item.custom_milk_type,
            custom_fat=item.custom_fat,
            custom_snf=item.custom_snf,
            weight_kg=weight_kg,
        )

        kg_per_litre = flt(res.get("kg_per_litre") or 1.0339)
        # item.qty = flt(res.get("qty_litre"), 3)
        item.conversion_factor = kg_per_litre
        # item.stock_qty = flt(item.qty * item.conversion_factor, 3)

        item.milk_rate_type = res.get("rate_type")
        item.milk_base_rate = flt(res.get("base_rate"), 3)
        item.milk_fat_addition = flt(res.get("fat_addition"), 3)
        item.milk_fat_deduction = flt(res.get("fat_deduction"), 3)
        item.milk_snf_addition = flt(res.get("snf_addition"), 3)
        item.milk_snf_deduction = flt(res.get("snf_deduction"), 3)
        item.milk_final_rate = flt(res.get("final_rate"), 3)
        item.milk_final_amount = flt(res.get("amount"), 2)
        item.milk_payable_fat_kg = flt(res.get("payable_fat_kg"), 3)
        item.milk_rate_per_litre_display = flt(res.get("rate_per_litre_display"), 3)

        if item.milk_rate_type == "Per Litre":
            item.rate = item.milk_final_rate
            item.amount = flt(item.qty * item.rate, 2)
        else:
            item.rate = item.milk_final_rate
            item.amount = item.milk_final_amount


#! Return only the stock UOM and item-specific conversion UOMs for use in UOM link field dropdowns.

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_allowed_uoms_for_item(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query to return only allowed UOMs for an item
    This is called by the Link field dropdown
    """
    item_code = filters.get('item_code')
    
    if not item_code:
        return []
    
    # Get stock UOM (always allowed)
    item = frappe.get_cached_doc('Item', item_code)
    stock_uom = item.stock_uom
    
    # Build SQL query to get UOMs from UOM Conversion Detail
    query = """
        SELECT DISTINCT uom as value, uom as description
        FROM `tabUOM Conversion Detail`
        WHERE parent = %(item_code)s
        AND parenttype = 'Item'
        AND docstatus < 2
        AND uom LIKE %(txt)s
        
        UNION
        
        SELECT %(stock_uom)s as value, %(stock_uom)s as description
        WHERE %(stock_uom)s LIKE %(txt)s
        
        ORDER BY value
        LIMIT %(page_len)s OFFSET %(start)s
    """
    
    return frappe.db.sql(query, {
        'item_code': item_code,
        'stock_uom': stock_uom,
        'txt': f'%{txt}%',
        'start': start,
        'page_len': page_len
    })


#! Validate that the selected UOM is permitted for the item based on stock UOM and defined conversions.
@frappe.whitelist()
def validate_item_uom(item_code, uom):
    """
    Validate if a UOM is allowed for an item
    Returns: dict with 'valid' boolean and optional 'message'
    """
    if not item_code or not uom:
        return {'valid': False, 'message': _('Item Code and UOM are required')}
    
    # Get item details
    item = frappe.get_cached_doc('Item', item_code)
    
    # Stock UOM is always valid
    if item.stock_uom == uom:
        return {'valid': True}
    
    # Check if UOM exists in conversion table
    uom_exists = frappe.db.exists('UOM Conversion Detail', {
        'parent': item_code,
        'parenttype': 'Item',
        'uom': uom,
        'docstatus': ['<', 2]
    })
    
    if uom_exists:
        return {'valid': True}
    
    # Get list of allowed UOMs for error message
    allowed_uoms = frappe.db.sql_list("""
        SELECT DISTINCT uom
        FROM `tabUOM Conversion Detail`
        WHERE parent = %s
        AND parenttype = 'Item'
        AND docstatus < 2
        ORDER BY uom
    """, item_code)
    
    # Add stock UOM to the list
    if item.stock_uom not in allowed_uoms:
        allowed_uoms.insert(0, item.stock_uom)
    
    return {
        'valid': False,
        'message': _('UOM <b>{0}</b> is not allowed for Item <b>{1}</b>.<br><br>Allowed UOMs: <b>{2}</b>').format(
            uom, 
            item_code, 
            ', '.join(allowed_uoms) if allowed_uoms else 'None'
        )
    }
    


# ! Prevent saving Purchase Receipt if a different item already has stock in a warehouse restricted to one item.

def validate_only_one_item_warehouse(doc, method=None):
    for row in doc.items:
        if not row.warehouse or not row.item_code:
            continue

        # Check warehouse flag
        if not frappe.db.get_value("Warehouse", row.warehouse, "custom_only_one_item"):
            continue

        # Check for any other item with stock > 0
        conflict = frappe.db.sql("""
            SELECT item_code, actual_qty
            FROM `tabBin`
            WHERE warehouse = %s
              AND actual_qty > 0
              AND item_code != %s
            LIMIT 1
        """, (row.warehouse, row.item_code), as_dict=True)

        if conflict:
            frappe.throw(_(
                "Warehouse <b>{0}</b> allows only one item at a time.<br>"
                "Item <b>{1}</b> already exists with quantity <b>{2}</b> (Stock UOM).<br>"
                "Please reduce its stock to zero before adding another item."
            ).format(
                row.warehouse,
                conflict[0].item_code,
                conflict[0].actual_qty
            ))

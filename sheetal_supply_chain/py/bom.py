import frappe
from frappe import _
from frappe.utils import flt

# ! Fetch latest FAT/SNF percentages from the last submitted Milk Quality Ledger Entry and calculate FAT/SNF KG for given quantity
@frappe.whitelist()
def get_last_mqle_values(item_code, warehouse,qty):
    """
    Fetch last Milk Quality Ledger Entry values for this item.
    Returns fat%, snf%, fat_kg, snf_kg
    """

# get last MQLE for this item
    last_mqle = frappe.db.get_value(
        "Milk Quality Ledger Entry",
        filters={"item_code":item_code, "warehouse": warehouse,"docstatus": 1},
        fieldname=["fat_per", "snf_per", "fat", "snf"],
        order_by="creation desc",
        as_dict=True,
    )


    if not last_mqle:
        return {}

    fat = flt(last_mqle.fat_per)
    snf = flt(last_mqle.snf_per)
    qty = flt(qty)

    # Calculate kg values
    fat_kg = (fat / 100) * qty
    snf_kg = (snf / 100) * qty

    return {
        "custom_fat": fat,
        "custom_snf": snf,
        "custom_fat_kg": fat_kg,
        "custom_snf_kg": snf_kg
    }

# ! Auto-populate FAT, SNF, and KG values on item rows during the first save using the last available Milk Quality Ledger Entry
def set_fat_snf_on_first_save(doc, method=None):

    # Only on first SAVE (new document)
    if not doc.get("__islocal"):
        return

    for item in doc.items:

        if not item.item_code or not item.qty:
            continue

        warehouse = item.custom_warehouse
        if not warehouse:
            continue

        # Call your custom function
        values = get_last_mqle_values(
            item_code=item.item_code,
            warehouse=warehouse,
            qty=item.qty
        )

        if not values:
            continue

        # Set values on item table
        item.custom_fat = values.get("custom_fat")
        item.custom_snf = values.get("custom_snf")
        item.custom_fat_kg = values.get("custom_fat_kg")
        item.custom_snf_kg = values.get("custom_snf_kg")


# ! Calculate and set total quantity, total FAT/SNF percentages, total FAT/SNF KG, and weighted FAT/SNF percentages on BOM
def set_bom_totals(doc, method=None):
    
    total_qty = 0
    total_fat_per = 0
    total_snf_per = 0
    total_fat_kg = 0
    total_snf_kg = 0

    for item in doc.items:
        total_qty += flt(item.qty)
        total_fat_per += flt(item.custom_fat)
        total_snf_per += flt(item.custom_snf)
        total_fat_kg += flt(item.custom_fat_kg)
        total_snf_kg += flt(item.custom_snf_kg)

    doc.custom_total_quantity = total_qty
    doc.custom_total_fat_percentage = total_fat_per
    doc.custom_total_snf_percentage = total_snf_per
    doc.custom_total_fat_kg = total_fat_kg
    doc.custom_total_snf_kg = total_snf_kg

    if total_qty:
        doc.custom_fat_percentage = (total_fat_kg / total_qty) * 100
        doc.custom_snf_percentage = (total_snf_kg / total_qty) * 100
    else:
        doc.custom_fat_percentage = 0
        doc.custom_snf_percentage = 0   



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
    


import frappe
from frappe.utils import flt
import frappe
from frappe.utils import add_days, getdate
from frappe.utils import add_days, getdate


#! Fetch FAT & SNF percentages from BOM items and calculate corresponding FAT/SNF kg values for Work Order required items based on required quantity
def fetch_bom_fat_snf_for_work_order(doc, method=None):
    
    if not doc.is_new():
        return

    if not doc.bom_no or not doc.required_items:
        return

    # Fetch BOM item FAT & SNF %
    bom_items = frappe.get_all(
        "BOM Item",
        filters={"parent": doc.bom_no},
        fields=["item_code", "custom_fat", "custom_snf"]
    )

    bom_map = {b.item_code: b for b in bom_items}

    for row in doc.required_items:
        # Skip finished item if flag exists
        if getattr(row, "is_finished_item", 0):
            continue

        bom_item = bom_map.get(row.item_code)
        if not bom_item:
            continue

        fat_per = flt(bom_item.custom_fat)
        snf_per = flt(bom_item.custom_snf)
        qty = flt(row.required_qty,3)

        row.custom_fat = fat_per
        row.custom_snf = snf_per
        row.custom_fat_kg = (fat_per * qty) / 100
        row.custom_snf_kg = (snf_per * qty) / 100



#! Calculates and sets total quantity, FAT/SNF percentages, and FAT/SNF weights on Work Order based on item-level values.
def set_work_order_totals(doc, method=None):

    # Initialize safely
    total_qty = 0.0
    total_fat_per = 0.0
    total_snf_per = 0.0
    total_fat_kg = 0.0
    total_snf_kg = 0.0 

    # If required_items table is empty or not loaded
    if not getattr(doc, "required_items", None):
        doc.custom_total_quantity = 0
        doc.custom_total_fat_percentage = 0
        doc.custom_total_snf_percentage = 0
        doc.custom_total_fat_kg = 0
        doc.custom_total_snf_kg = 0
        doc.custom_fat_percentage = 0
        doc.custom_snf_percentage = 0
        
        
        return

    for item in doc.required_items:
        qty = flt(getattr(item, "required_qty", 0), 3)
        fat = flt(getattr(item, "custom_fat", 0))
        snf = flt(getattr(item, "custom_snf", 0))
        fat_kg = flt(getattr(item, "custom_fat_kg", 0))
        snf_kg = flt(getattr(item, "custom_snf_kg", 0))
      
        total_qty += qty
        total_fat_per += fat
        total_snf_per += snf
        total_fat_kg += fat_kg
        total_snf_kg += snf_kg
        
    # Set totals on parent
    doc.custom_total_quantity = flt(total_qty,3)
    doc.custom_total_fat_percentage = flt(total_fat_per,3)
    doc.custom_total_snf_percentage = flt(total_snf_per,3)
    doc.custom_total_fat_kg = flt(total_fat_kg,3)
    doc.custom_total_snf_kg = flt(total_snf_kg,3)
    
    # Final weighted percentage calculation
    if doc.custom_total_quantity:
        doc.custom_fat_percentage = flt(
            (doc.custom_total_fat_kg / doc.custom_total_quantity) * 100, 3)
        doc.custom_snf_percentage = flt(
            (doc.custom_total_snf_kg / doc.custom_total_quantity) * 100, 3)
    else:
        doc.custom_fat_percentage = 0
        doc.custom_snf_percentage = 0
        
  
      
#! Fetches and returns the Primary UOM configured for the given Item from its UOM Conversion Detail   
@frappe.whitelist()
def get_primary_uom_from_item(item_code):
    if not item_code:
        return None

    # Fetch primary UOM from Item UOM Conversion Detail
    primary_uom = frappe.db.get_value(
        "UOM Conversion Detail",
        {
            "parent": item_code,
            "parenttype": "Item",
            "custom_is_primary_uom": 1
        },
        "uom"
    )

    return primary_uom



#! Fetches and returns the Secondary UOM configured for the given Item from its UOM Conversion Detail

@frappe.whitelist()
def get_secondary_uom_from_item(item_code):
    if not item_code:
        return None

    # Fetch primary UOM from Item UOM Conversion Detail
    secondary_uom = frappe.db.get_value(
        "UOM Conversion Detail",
        {
            "parent": item_code,
            "parenttype": "Item",
            "custom_is_secondary_uom": 1
        },
        "uom"
    )

    return secondary_uom


#! Calculates and returns the Primary UOM quantity for a Work Order by converting the given WO quantity from Stock UOM using the Item’s Primary UOM conversion factor

@frappe.whitelist()
def get_primary_uom_qty(item_code, wo_qty):
    """
    Returns primary UOM quantity based on stock UOM and conversion factor
    """

    if not item_code or not wo_qty:
        return 0

    # FIX: convert to float
    wo_qty = float(wo_qty)

    item = frappe.get_doc("Item", item_code)

    stock_uom = item.stock_uom
    primary_uom = None
    conversion_factor = None

    for row in item.uoms:
        if row.custom_is_primary_uom:
            primary_uom = row.uom
            conversion_factor = row.conversion_factor
            break

    if not primary_uom:
        frappe.throw(frappe._("Primary UOM not defined in Item Master"))

    if stock_uom == primary_uom:
        return wo_qty

    if not conversion_factor:
        frappe.throw(frappe._("Conversion factor missing for Primary UOM"))

    return wo_qty / float(conversion_factor)


#! Creates Crate Master records for the given Work Order based on Secondary UOM quantity, setting manufacturing/expiry dates and linking each crate to the Work Order and production item

@frappe.whitelist()
def create_crate_master_for_secondary_uom(work_order, qty):

    wo = frappe.get_doc("Work Order", work_order)

    if not wo.production_item:
        frappe.throw("Production Item not found in Work Order")

    if not wo.custom_posting_date:
        frappe.throw("Posting Date is not set in Work Order")

    shelf_life = frappe.db.get_value(
        "Item",
        wo.production_item,
        "shelf_life_in_days"
    ) or 0

    manu_date = getdate(wo.custom_posting_date)
    expiry_date = add_days(manu_date, shelf_life)

    for _ in range(int(qty)):
        crate = frappe.new_doc("Crate Master")

        crate.item = wo.production_item
        crate.batch = wo.custom_batch_no
        crate.manufacturing_date = manu_date
        crate.expiry_date = expiry_date
        crate.work_order = wo.name
        crate.box_convesion_qty = wo.custom_printed_qty_for_secondary_uom
        crate.status = "Empty"

        crate.insert(ignore_permissions=True)

    frappe.db.commit()



# @frappe.whitelist()
# def get_secondary_uom_qty(item_code, wo_qty):
#     """
#     Calculates secondary UOM qty using ratio of conversion factors
#     """

#     if not item_code or not wo_qty:
#         return 0

#     wo_qty = float(wo_qty)

#     item = frappe.get_doc("Item", item_code)

#     primary_cf = None
#     secondary_cf = None

#     for row in item.uoms:
#         if row.custom_is_primary_uom:
#             primary_cf = row.conversion_factor
#         if row.custom_is_secondary_uom:
#             secondary_cf = row.conversion_factor

#     if not primary_cf or not secondary_cf:
#         frappe.throw(frappe._("Primary or Secondary UOM not defined in Item Master"))

#     # difference = secondary / primary
#     difference = float(secondary_cf) / float(primary_cf)

#     if not difference:
#         frappe.throw(frappe._("Invalid UOM conversion factors"))

#     return wo_qty / difference


@frappe.whitelist()
def get_secondary_uom_qty(item_code, primary_qty):
    """
    Calculates secondary UOM qty using primary UOM qty and conversion factor ratio
    """

    if not item_code or not primary_qty:
        return 0

    primary_qty = float(primary_qty)

    item = frappe.get_doc("Item", item_code)

    primary_cf = None
    secondary_cf = None

    for row in item.uoms:
        if row.custom_is_primary_uom:
            primary_cf = row.conversion_factor
        if row.custom_is_secondary_uom:
            secondary_cf = row.conversion_factor

    if not primary_cf or not secondary_cf:
        frappe.throw(frappe._("Primary or Secondary UOM not defined in Item Master"))

    difference = float(secondary_cf) / float(primary_cf)

    if not difference:
        frappe.throw(frappe._("Invalid UOM conversion factors"))

    # Now divide primary_qty by difference
    return primary_qty / difference

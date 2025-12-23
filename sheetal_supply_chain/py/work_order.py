import frappe
from frappe.utils import flt


# Fetch FAT & SNF percentages from BOM items and calculate corresponding FAT/SNF kg values for Work Order required items based on required quantity
def fetch_bom_fat_snf_for_work_order(doc, method=None):
    if not doc.bom_no:
        return

    if not doc.required_items:
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
    if total_qty:
        doc.custom_fat_percentage = flt((total_fat_kg / total_qty) * 100,3)
        doc.custom_snf_percentage = flt((total_snf_kg / total_qty) * 100, 3)
    else:
        doc.custom_fat_percentage = 0
        doc.custom_snf_percentage = 0

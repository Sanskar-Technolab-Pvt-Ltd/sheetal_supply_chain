import frappe
def qi_reading(doc, method):
    for row in doc.readings:
        if not row.numeric:
            if row.status == "Accepted":
                row.reading_value = "Ok"
            elif row.status == "Rejected":
                row.reading_value = "Not Ok"
        else:
            row.reading_value = ""




import frappe

# def create_mqle_on_qi_submit(doc, method=None):
#     """
#     Create Milk Quality Ledger Entry (MQLE) on Quality Inspection Submit.
#     Only for inspection_type == 'Internal'.
#     """

#     if doc.inspection_type != "Internal":
#         return

#     # Initialize FAT and SNF percentages
#     fat_per = snf_per = 0.0

#     # Loop through readings to get FAT and SNF
#     for reading in getattr(doc, "readings", []):
#         value = reading.reading_1 or 0
#         try:
#             value = float(value)
#         except (ValueError, TypeError):
#             value = 0.0

#         if reading.specification.upper() == "FAT":
#             fat_per = value
#         elif reading.specification.upper() in ("S.N.F.", "SNF"):
#             snf_per = value

#     # Fetch latest MQLE entry to get qty_in_liter and qty_in_kg
#     latest_mqle = frappe.get_all(
#         "Milk Quality Ledger Entry",
#         filters={
#             "item_code": doc.item_code,
#             "warehouse": doc.custom_warehouse
#         },
#         order_by="creation desc",
#         limit_page_length=1,
#         fields=["qty_in_liter", "qty_in_kg"]
#     )

#     if latest_mqle:
#         qty_in_liter = float(latest_mqle[0].qty_in_liter or 0)
#         qty_in_kg = float(latest_mqle[0].qty_in_kg or 0)
#     else:
#         qty_in_liter = qty_in_kg = 0.0

#     # Calculate fat and snf
#     fat = fat_per * qty_in_kg
#     snf = snf_per * qty_in_kg

#     # Create MQLE document
#     mqle = frappe.new_doc("Milk Quality Ledger Entry")
#     mqle.item_code = doc.item_code
#     mqle.item_name = doc.item_name
#     mqle.warehouse = doc.custom_warehouse

#     mqle.voucher_type = "Quality Inspection"
#     mqle.voucher_no = doc.name
#     mqle.voucher_detail_no = None  # No child table row

#     mqle.posting_date = doc.report_date or frappe.utils.nowdate()
#     mqle.posting_time = frappe.utils.nowtime()

#     mqle.actual_quantity = qty_in_kg
    
#     item_uoms = frappe.get_value(
#         "Item",
#         doc.item_code,
#         ["stock_uom", "purchase_uom"],
#         as_dict=True
#     )
#     mqle.stock_uom = item_uoms.get("stock_uom") if item_uoms and item_uoms.get("stock_uom") else "KG"
#     mqle.uom = item_uoms.get("purchase_uom") if item_uoms and item_uoms.get("purchase_uom") else "Litre"

#     mqle.fat_per = fat_per
#     mqle.snf_per = snf_per
#     mqle.fat = fat
#     mqle.snf = snf

#     mqle.qty_in_liter = qty_in_liter
#     mqle.qty_in_kg = qty_in_kg

#     # Save and submit
#     mqle.save(ignore_permissions=True)
#     mqle.submit()

#     frappe.msgprint(f"Milk Quality Ledger Entry Created for Quality Inspection {doc.name}.")




# def create_mqle_on_qi_submit(doc, method=None):
#     """
#     Create Milk Quality Ledger Entry (MQLE) on Quality Inspection Submit.
#     Only for inspection_type == 'Internal'.
#     """
 
#     if doc.inspection_type != "Internal":
#         return
 
#     # Initialize FAT and SNF percentages
#     fat_per = snf_per = 0.0
 
#     # Loop through readings to get FAT and SNF
#     for reading in getattr(doc, "readings", []):
#         value = reading.reading_1 or 0
#         try:
#             value = float(value)
#         except (ValueError, TypeError):
#             value = 0.0
 
#         if reading.specification.upper() == "FAT":
#             fat_per = value
#         elif reading.specification.upper() in ("S.N.F.", "SNF"):
#             snf_per = value
 
#     # Fetch latest MQLE entry to get qty_in_kg (balance in default UOM)
#     latest_mqle = frappe.get_all(
#         "Milk Quality Ledger Entry",
#         filters={
#             "item_code": doc.item_code,
#             "warehouse": doc.custom_warehouse
#         },
#         order_by="creation desc",
#         limit_page_length=1,
#         fields=["qty_in_liter", "qty_in_kg"]
#     )
 
#     if latest_mqle:
#         qty_in_kg = float(latest_mqle[0].qty_in_kg or 0)
#     else:
#         qty_in_kg = 0.0
 
#     # Fetch stock_uom of the item
#     item_uoms = frappe.get_value(
#         "Item",
#         doc.item_code,
#         ["stock_uom", "purchase_uom"],
#         as_dict=True
#     )
#     stock_uom = item_uoms.get("stock_uom") if item_uoms and item_uoms.get("stock_uom") else "KG"
#     included_uom = "Litre"
 
#     # Get conversion factor from stock UOM -> Litre
#     conversion_factor = frappe.db.get_value(
#         "UOM Conversion Detail",
#         {"parent": doc.item_code, "uom": included_uom},
#         "conversion_factor"
#     ) or 1
 
#     # Calculate balance in included UOM
#     qty_in_litre = qty_in_kg / conversion_factor if stock_uom != included_uom else qty_in_kg
 
#     # Calculate fat and snf
#     fat = fat_per * qty_in_kg
#     snf = snf_per * qty_in_kg
 
#     # Create MQLE document
#     mqle = frappe.new_doc("Milk Quality Ledger Entry")
#     mqle.item_code = doc.item_code
#     mqle.item_name = doc.item_name
#     mqle.warehouse = doc.custom_warehouse
 
#     mqle.voucher_type = "Quality Inspection"
#     mqle.voucher_no = doc.name
#     mqle.voucher_detail_no = None  # No child table row
 
#     mqle.posting_date = doc.report_date or frappe.utils.nowdate()
#     mqle.posting_time = frappe.utils.nowtime()
 
#     mqle.actual_quantity = qty_in_kg
 
#     mqle.stock_uom = stock_uom
#     mqle.uom = included_uom
 
#     mqle.fat_per = fat_per
#     mqle.snf_per = snf_per
#     mqle.fat = fat
#     mqle.snf = snf
 
#     # Balance quantities
#     mqle.qty_in_kg = qty_in_kg
#     mqle.qty_in_liter = qty_in_litre
 
#     # Save and submit
#     mqle.save(ignore_permissions=True)
#     mqle.submit()
 
#     frappe.msgprint(f"Milk Quality Ledger Entry Created for Quality Inspection {doc.name}.")  
    
from erpnext.stock.utils import get_stock_balance, get_combine_datetime, get_default_stock_uom

def create_mqle_on_qi_submit(doc, method=None):
    if doc.inspection_type != "Internal":
        return

    # Initialize FAT and SNF percentages
    fat_per = snf_per = 0.0
    for reading in getattr(doc, "readings", []):
        value = reading.reading_1 or 0
        try:
            value = float(value)
        except (ValueError, TypeError):
            value = 0.0

        if reading.specification.upper() == "FAT":
            fat_per = value
        elif reading.specification.upper() in ("S.N.F.", "SNF"):
            snf_per = value

    # Get latest balance from Stock Ledger
    posting_date = doc.report_date or frappe.utils.nowdate()
    posting_time = frappe.utils.nowtime()

    stock_qty = get_stock_balance(
        item_code=doc.item_code,
        warehouse=doc.custom_warehouse,
        posting_date=posting_date,
        posting_time=posting_time,
        with_valuation_rate=False,
        with_serial_no=False
    )

    # Get default stock UOM
    stock_uom = frappe.get_cached_value("Item", doc.item_code, "stock_uom") or "KG"
    included_uom = "Litre"

    # Get conversion factor from stock UOM -> included UOM
    conversion_factor = frappe.db.get_value(
        "UOM Conversion Detail",
        {"parent": doc.item_code, "uom": included_uom},
        "conversion_factor"
    ) or 1.0

    # Convert qty to included UOM
    qty_in_litre = stock_qty / conversion_factor if stock_uom != included_uom else stock_qty

    # Calculate fat and snf
    fat = fat_per * stock_qty
    snf = snf_per * stock_qty

    # Create MQLE document
    mqle = frappe.new_doc("Milk Quality Ledger Entry")
    mqle.item_code = doc.item_code
    mqle.item_name = doc.item_name
    mqle.warehouse = doc.custom_warehouse

    mqle.voucher_type = "Quality Inspection"
    mqle.voucher_no = doc.name
    mqle.voucher_detail_no = None

    mqle.posting_date = posting_date
    mqle.posting_time = posting_time

    mqle.actual_quantity = stock_qty
    mqle.stock_uom = stock_uom
    mqle.uom = included_uom

    mqle.fat_per = fat_per
    mqle.snf_per = snf_per
    mqle.fat = fat
    mqle.snf = snf

    mqle.qty_in_kg = stock_qty
    mqle.qty_in_liter = qty_in_litre

    mqle.save(ignore_permissions=True)
    mqle.submit()

    frappe.msgprint(f"Milk Quality Ledger Entry Created for Quality Inspection {doc.name}.")


def cancel_mqle_on_qi_cancel(doc, method=None):
    """
    Cancel MQLE when Quality Inspection is cancelled.
    Only for Internal inspection_type.
    """

    if doc.inspection_type != "Internal":
        return

    # Find MQLE linked to this Quality Inspection
    mqle_list = frappe.get_all(
        "Milk Quality Ledger Entry",
        filters={
            "voucher_type": "Quality Inspection",
            "voucher_no": doc.name
        },
        fields=["name", "docstatus"]
    )

    if not mqle_list:
        return  # No MQLE found → nothing to cancel

    for mqle in mqle_list:
        if mqle.docstatus == 1:   # Submitted
            mqle_doc = frappe.get_doc("Milk Quality Ledger Entry", mqle.name)
            mqle_doc.is_cancelled = 1
            mqle_doc.cancel()
            frappe.msgprint(f"Milk Quality Ledger Entry {mqle.name} cancelled.")



# @frappe.whitelist()
# def get_items_with_stock(doctype, txt, searchfield, start, page_len, filters):
#     warehouse = filters.get("warehouse")
#     if not warehouse:
#         return []

#     # Fetch items having stock > 0 in this warehouse
#     items = frappe.db.sql("""
#         SELECT 
#             item_code, item_name
#         FROM 
#             `tabBin`
#         WHERE 
#             warehouse = %s
#             AND actual_qty > 0
#             AND item_code LIKE %s
#         ORDER BY 
#             item_code
#         LIMIT %s OFFSET %s
#     """, (warehouse, "%" + txt + "%", page_len, start))

#     return items



# @frappe.whitelist()
# def get_items_with_stock(doctype, txt, searchfield, start, page_len, filters):
#     warehouse = filters.get("warehouse")
#     if not warehouse:
#         return []

#     search_text = f"%{txt}%"

#     items = frappe.db.sql("""
#         SELECT 
#             bin.item_code,
#             bin.item_code   -- second column = label (safe and always available)
#         FROM 
#             `tabBin` bin
#         WHERE
#             bin.warehouse = %s
#             AND bin.actual_qty > 0
#             AND (
#                 bin.item_code LIKE %s
#             )
#         ORDER BY 
#             bin.item_code
#         LIMIT %s OFFSET %s
#     """, (warehouse, search_text, page_len, start))

#     return items
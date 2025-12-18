import frappe
from frappe import _
from erpnext.stock.utils import get_stock_balance
from frappe.utils import nowdate, nowtime, flt
from datetime import datetime

 
#  ! Fetch latest FAT/SNF values from Quality Inspection and calculate FAT/SNF KG based on given quantity (used for real-time JS updates)
@frappe.whitelist()
def update_fat_snf_js(qi, qty=None):
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
    qty = frappe.utils.flt(qty or 0)
    return {
        "fat": fat,
        "snf": snf,
        "fat_kg": (fat/100) * qty,
        "snf_kg": (snf/100) * qty
    }
 
 

# ! Create Milk Quality Ledger Entries (MQLE) for FINISHED milk items when Stock Entry of type Manufacture is submitted
def create_mqle_on_se_submit(doc, method=None):
    """
    Create Milk Quality Ledger Entry (MQLE) on Stock Entry Submit
    """
        # ------------------------------------
    if doc.stock_entry_type != "Manufacture":
        return
    
    posting_date = doc.posting_date or nowdate()
    posting_time = doc.posting_time or nowtime()

    for row in doc.items:

        # Only Milk items
        if not (row.is_finished_item and row.custom_is_milk_type):
            continue

        # -------------------------------
        # Get balance AFTER transaction
        # -------------------------------
        stock_qty_after = get_stock_balance(
            item_code=row.item_code,
            warehouse=row.t_warehouse or row.s_warehouse,
            posting_date=posting_date,
            posting_time=posting_time,
            with_valuation_rate=False,
            with_serial_no=False
        )
        
        
        # -------------------------------
        # Fetch Batch No
        # -------------------------------
        batch_no = None

        if row.batch_no:
            batch_no = row.batch_no
        elif row.serial_and_batch_bundle:
            bundle = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
            for e in bundle.entries:
                if e.batch_no:
                    batch_no = e.batch_no
                    break
                
        
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

        # -------------------------------
        # Incoming qty (THIS transaction)
        # -------------------------------
        in_qty_in_kg = flt(row.qty)
        in_qty_in_liter = (
            flt(row.qty) / conversion_factor
            if stock_uom != included_uom
            else flt(row.qty)
        )

        # -------------------------------
        # Create MQLE
        # -------------------------------
        mqle = frappe.new_doc("Milk Quality Ledger Entry")

        # Basic
        mqle.item_code = row.item_code
        mqle.item_name = row.item_name
        mqle.warehouse = row.t_warehouse or row.s_warehouse

        mqle.voucher_type = doc.doctype
        mqle.voucher_no = doc.name
        mqle.voucher_detail_no = row.name
        mqle.batch_no = batch_no
        mqle.posting_date = posting_date
        mqle.posting_time = posting_time

        # UOM
        mqle.stock_uom = stock_uom
        mqle.uom = included_uom

        # Milk params
        mqle.fat_per = row.custom_fat
        mqle.snf_per = row.custom_snf
        mqle.fat = row.custom_fat_kg
        mqle.snf = row.custom_snf_kg

        # -------------------------------
        #  REQUIRED FIELD MAPPING 
        # -------------------------------
        mqle.qty_in_liter = in_qty_in_liter
        mqle.qty_in_kg = in_qty_in_kg

        mqle.qty_after_transaction_in_liter = qty_after_litre
        mqle.qty_after_transaction_in_kg = stock_qty_after

        # Save & Submit
        mqle.save(ignore_permissions=True)
        mqle.submit()



# ! Create MQLE entries for milk items during Material Issue Stock Entry using last recorded milk quality
def create_mqle_for_raw_materials(doc, method=None):
    """
    Create MQLE for raw material milk items on Stock Entry Submit
    (is_finished_item = 0 AND custom_is_milk_type = 1)
    """
        # ------------------------------------
    if doc.stock_entry_type != "Manufacture":
        return
    
    posting_date = doc.posting_date or nowdate()
    posting_time = doc.posting_time or nowtime()

    for row in doc.items:

        # Only RAW MATERIAL milk items
        if not (not row.is_finished_item and row.custom_is_milk_type):
            continue

        warehouse = row.t_warehouse or row.s_warehouse

        # -------------------------------
        #  Get balance AFTER transaction
        # -------------------------------
        stock_qty_after = get_stock_balance(
            item_code=row.item_code,
            warehouse=warehouse,
            posting_date=posting_date,
            posting_time=posting_time,
            with_valuation_rate=False,
            with_serial_no=False
        )

        # -------------------------------
        #  Get latest MQLE for FAT/SNF
        # -------------------------------
        last_mqle = frappe.db.get_value(
            "Milk Quality Ledger Entry",
            filters={"item_code": row.item_code, "warehouse": warehouse,"docstatus": 1},
            fieldname=["fat_per", "snf_per", "fat", "snf"],
            order_by="creation desc",
            as_dict=True,
        )

        fat_per = last_mqle.fat_per if last_mqle else 0
        snf_per = last_mqle.snf_per if last_mqle else 0

        # -------------------------------
        #  UOM handling
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

        # -------------------------------
        #  OUTGOING QTY (RAW MATERIAL)
        # -------------------------------
        out_qty_in_kg = flt(row.qty)
        out_qty_in_liter = (
            flt(row.qty) / conversion_factor
            if stock_uom != included_uom
            else flt(row.qty)
        )
        
        # -------------------------------
        #  Fetch Batch No
        # -------------------------------
        
        
        batch_no = None

        # 1) If batch directly selected in Stock Entry Row
        if row.batch_no:
            batch_no = row.batch_no

        # 2) If Serial and Batch Bundle is used
        elif row.serial_and_batch_bundle:
            bundle = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
            for e in bundle.entries:
                if e.batch_no:
                    batch_no = e.batch_no
                    break

        # -------------------------------
        #  Create MQLE
        # -------------------------------
        mqle = frappe.new_doc("Milk Quality Ledger Entry")

        mqle.item_code = row.item_code
        mqle.item_name = row.item_name
        mqle.warehouse = warehouse

        mqle.voucher_type = doc.doctype
        mqle.voucher_no = doc.name
        mqle.voucher_detail_no = row.name

        mqle.posting_date = posting_date
        mqle.posting_time = posting_time
        mqle.batch_no = batch_no
        mqle.stock_uom = stock_uom
        mqle.uom = included_uom

        # Milk params from LAST MQLE
        mqle.fat_per = fat_per
        mqle.snf_per = snf_per
        mqle.fat = (fat_per * out_qty_in_kg/100)
        mqle.snf = (snf_per * out_qty_in_kg/100)

        # OUTGOING QTY instead of incoming qty
        mqle.qty_in_liter = out_qty_in_liter
        mqle.qty_in_kg = out_qty_in_kg

        mqle.qty_after_transaction_in_liter = qty_after_litre
        mqle.qty_after_transaction_in_kg = stock_qty_after

        mqle.save(ignore_permissions=True)
        mqle.submit()


# ! Create MQLE entries for milk items during Material Issue Stock Entry using last recorded milk quality
def create_mqle_for_raw_materials_issue(doc, method=None):
    """
    Create MQLE for milk items on Stock Entry Submit
    Conditions:
        - Stock Entry Type = Material Issue
        - custom_is_milk_type = 1
    """

    # Run ONLY for Material Issue
    if doc.stock_entry_type != "Material Issue":
        return

    posting_date = doc.posting_date or nowdate()
    posting_time = doc.posting_time or nowtime()

    for row in doc.items:

        # Only milk items (remove is_finished_item condition)
        if row.custom_is_milk_type != 1:
            continue

        warehouse = row.t_warehouse or row.s_warehouse

        # -------------------------------
        #  Get balance AFTER transaction
        # -------------------------------
        stock_qty_after = get_stock_balance(
            item_code=row.item_code,
            warehouse=warehouse,
            posting_date=posting_date,
            posting_time=posting_time,
            with_valuation_rate=False,
            with_serial_no=False
        )

        # -------------------------------
        #  Latest MQLE for FAT/SNF
        # -------------------------------
        last_mqle = frappe.db.get_value(
            "Milk Quality Ledger Entry",
            filters={"item_code": row.item_code, "warehouse": warehouse,"docstatus": 1},
            fieldname=["fat_per", "snf_per", "fat", "snf"],
            order_by="creation desc",
            as_dict=True,
        )

        fat_per = last_mqle.fat_per if last_mqle else 0
        snf_per = last_mqle.snf_per if last_mqle else 0
     

        # -------------------------------
        #  UOM handling
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

        # -------------------------------
        #  OUTGOING QTY (Material Issue)
        # -------------------------------
        out_qty_in_kg = flt(row.qty)
        out_qty_in_liter = (
            flt(row.qty) / conversion_factor
            if stock_uom != included_uom
            else flt(row.qty)
        )

        # -------------------------------
        #  Fetch Batch No
        # -------------------------------
        
        
        batch_no = None

        # If batch directly selected in Stock Entry Row
        if row.batch_no:
            batch_no = row.batch_no

        # If Serial and Batch Bundle is used
        elif row.serial_and_batch_bundle:
            bundle = frappe.get_doc("Serial and Batch Bundle", row.serial_and_batch_bundle)
            for e in bundle.entries:
                if e.batch_no:
                    batch_no = e.batch_no
                    break

        # -------------------------------
        #  Create MQLE
        # -------------------------------
        mqle = frappe.new_doc("Milk Quality Ledger Entry")

        mqle.item_code = row.item_code
        mqle.item_name = row.item_name
        mqle.warehouse = warehouse

        mqle.voucher_type = doc.doctype
        mqle.voucher_no = doc.name
        mqle.voucher_detail_no = row.name

        mqle.posting_date = posting_date
        mqle.posting_time = posting_time
        mqle.batch_no = batch_no 
        mqle.stock_uom = stock_uom
        mqle.uom = included_uom

        # Milk params from LAST MQLE
        mqle.fat_per = fat_per
        mqle.snf_per = snf_per
        mqle.fat = (fat_per * out_qty_in_kg/100)
        mqle.snf = (snf_per * out_qty_in_kg/100)

        # OUTGOING QTY
        mqle.qty_in_liter = out_qty_in_liter
        mqle.qty_in_kg = out_qty_in_kg

        mqle.qty_after_transaction_in_liter = qty_after_litre
        mqle.qty_after_transaction_in_kg = stock_qty_after

        mqle.save(ignore_permissions=True)
        mqle.submit()



# ! Cancel all Milk Quality Ledger Entries linked to a Stock Entry when that Stock Entry is cancelled
def cancel_mqle_on_se_cancel(doc, method=None):
    """
    Cancel all MQLE entries created from this Stock Entry
    when Stock Entry is cancelled.
    """

    # Find MQLE linked to this Stock Entry
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


# ! Calculate and set total quantity, total FAT/SNF percentages, total FAT/SNF KG, and weighted FAT/SNF percentages on Stock Entry
def fetch_bom_fat_snf_for_manufacture(doc, method=None):
    if doc.stock_entry_type != "Manufacture":
        return

    if not doc.bom_no:
        return

    doc.custom_production_order = ""
    # Fetch BOM items (only % values)
    bom_items = frappe.get_all(
        "BOM Item",
        filters={"parent": doc.bom_no},
        fields=["item_code", "custom_fat", "custom_snf"]
    )

    bom_map = {b.item_code: b for b in bom_items}

    for row in doc.items:
        # Skip finished items
        if row.is_finished_item:
            continue

        bom_item = bom_map.get(row.item_code)
        if not bom_item:
            continue

        fat_per = flt(bom_item.custom_fat)
        snf_per = flt(bom_item.custom_snf)
        qty = flt(row.qty)

        row.custom_fat = fat_per
        row.custom_snf = snf_per
        row.custom_fat_kg = (fat_per * qty) / 100
        row.custom_snf_kg = (snf_per * qty) / 100


# Calculates and sets total quantity, FAT/SNF percentages, and FAT/SNF weights on Stock Entry based on item-level values.

def set_stock_entry_totals(doc, method=None):
    # Initialize safely
    total_qty = 0.0
    total_fat_per = 0.0
    total_snf_per = 0.0
    total_fat_kg = 0.0
    total_snf_kg = 0.0

    # If items table is empty or not loaded
    if not getattr(doc, "items", None):
        doc.custom_total_quantity = 0
        doc.custom_total_fat_percentage = 0
        doc.custom_total_snf_percentage = 0
        doc.custom_total_fat_kg = 0
        doc.custom_total_snf_kg = 0
        doc.custom_fat_percentage = 0
        doc.custom_snf_percentage = 0
        return

    for item in doc.items:
        # Defensive access (no AttributeError)
        qty = flt(getattr(item, "qty", 0))
        fat = flt(getattr(item, "custom_fat", 0))
        snf = flt(getattr(item, "custom_snf", 0))
        fat_kg = flt(getattr(item, "custom_fat_kg", 0))
        snf_kg = flt(getattr(item, "custom_snf_kg", 0))

        total_qty += qty
        total_fat_per += fat
        total_snf_per += snf
        total_fat_kg += fat_kg
        total_snf_kg += snf_kg

    # Set totals (same fields, same meaning)
    doc.custom_total_quantity = flt(total_qty)
    doc.custom_total_fat_percentage = flt(total_fat_per)
    doc.custom_total_snf_percentage = flt(total_snf_per)
    doc.custom_total_fat_kg = flt(total_fat_kg)
    doc.custom_total_snf_kg = flt(total_snf_kg)

    # Final percentage calculation (same logic)
    if total_qty:
        doc.custom_fat_percentage = flt((total_fat_kg / total_qty) * 100)
        doc.custom_snf_percentage = flt((total_snf_kg / total_qty) * 100)
    else:
        doc.custom_fat_percentage = 0
        doc.custom_snf_percentage = 0



# Auto-generates a date-wise sequential Production Order number for Manufacture Stock Entries, reusing cancelled numbers where possible.
def generate_production_order(doc, method=None):

    if doc.stock_entry_type != "Manufacture":
        return

    if doc.custom_production_order:
        return

    today = datetime.strptime(nowdate(), "%Y-%m-%d")
    date_part = today.strftime("%d%m%y")
    prefix = f"WO-{date_part}-"

    # Fetch all SUBMITTED counters
   
    submitted = frappe.db.sql("""
        SELECT custom_production_order
        FROM `tabStock Entry`
        WHERE
            stock_entry_type = 'Manufacture'
            AND docstatus = 1
            AND custom_production_order LIKE %s
    """, (prefix + "%",), as_dict=True)

    submitted_numbers = sorted(
        int(d.custom_production_order.split("-")[-1])
        for d in submitted
    )

    # Fetch all CANCELLED counters

    cancelled = frappe.db.sql("""
        SELECT custom_production_order
        FROM `tabStock Entry`
        WHERE
            stock_entry_type = 'Manufacture'
            AND docstatus = 2
            AND custom_production_order LIKE %s
    """, (prefix + "%",), as_dict=True)

    cancelled_numbers = sorted(
        int(d.custom_production_order.split("-")[-1])
        for d in cancelled
    )

    # CASE 1
    
    if not submitted_numbers and cancelled_numbers:
        reuse_no = cancelled_numbers[0]
        doc.db_set(
            "custom_production_order",
            f"{prefix}{str(reuse_no).zfill(5)}",
            update_modified=False
        )
        return

    # CASE 2

    if submitted_numbers and cancelled_numbers:
        max_submitted = max(submitted_numbers)

        eligible = [n for n in cancelled_numbers if n > max_submitted]
        if eligible:
            reuse_no = min(eligible)
            doc.db_set(
                "custom_production_order",
                f"{prefix}{str(reuse_no).zfill(5)}",
                update_modified=False
            )
            return


    # CASE 3

    next_no = max(submitted_numbers) + 1 if submitted_numbers else 1
    doc.db_set(
        "custom_production_order",
        f"{prefix}{str(next_no).zfill(5)}",
        update_modified=False
    )

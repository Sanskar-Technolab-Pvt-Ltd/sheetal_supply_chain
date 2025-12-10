import frappe
from frappe import _
 
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
        "fat_kg": fat * qty,
        "snf_kg": snf * qty
    }
 
 
from erpnext.stock.utils import get_stock_balance
import frappe
from frappe.utils import nowdate, nowtime, flt


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

    frappe.msgprint("Milk Quality Ledger Entries Created for Stock Entry.")



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
        mqle.fat = (fat_per * out_qty_in_kg)
        mqle.snf = (snf_per * out_qty_in_kg)

        # OUTGOING QTY instead of incoming qty
        mqle.qty_in_liter = out_qty_in_liter
        mqle.qty_in_kg = out_qty_in_kg

        mqle.qty_after_transaction_in_liter = qty_after_litre
        mqle.qty_after_transaction_in_kg = stock_qty_after

        mqle.save(ignore_permissions=True)
        mqle.submit()

    frappe.msgprint("MQLE created for RAW MATERIAL milk items.")


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
        mqle.fat = (fat_per * out_qty_in_kg)
        mqle.snf = (snf_per * out_qty_in_kg)

        # OUTGOING QTY
        mqle.qty_in_liter = out_qty_in_liter
        mqle.qty_in_kg = out_qty_in_kg

        mqle.qty_after_transaction_in_liter = qty_after_litre
        mqle.qty_after_transaction_in_kg = stock_qty_after

        mqle.save(ignore_permissions=True)
        mqle.submit()

    frappe.msgprint("MQLE created for Milk Items (Material Issue).")



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

    frappe.msgprint("Milk Quality Ledger Entries Cancelled (linked to this Stock Entry).")

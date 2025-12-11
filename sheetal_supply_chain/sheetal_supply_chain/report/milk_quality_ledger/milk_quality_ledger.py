# Copyright (c) 2025
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, cint
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce


def execute(filters=None):
    """Main entry point for the report"""
    filters = frappe._dict(filters or {})
    
    # Validate filters
    validate_filters(filters)
    
    columns = get_columns()
    entries = get_entries(filters)
    data = [build_row(e, filters) for e in entries]
    
    return columns, data


def validate_filters(filters):
    """Validate required filters and date ranges"""
    if not filters.get("company"):
        frappe.throw(_("Company is mandatory"))
    
    if not filters.get("from_date"):
        frappe.throw(_("From Date is mandatory"))
    
    if not filters.get("to_date"):
        frappe.throw(_("To Date is mandatory"))
    
    # Validate date range
    from_date = get_datetime(filters.from_date)
    to_date = get_datetime(filters.to_date)
    
    if from_date > to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))
    
    # Validate company exists
    if not frappe.db.exists("Company", filters.company):
        frappe.throw(_("Company {0} does not exist").format(filters.company))
    
    # Validate item codes if provided
    if filters.get("item_code"):
        if isinstance(filters.item_code, str):
            filters.item_code = [filters.item_code]
        
        for item in filters.item_code:
            if not frappe.db.exists("Item", item):
                frappe.throw(_("Item {0} does not exist").format(item))
    
    # Validate warehouses if provided
    if filters.get("warehouse"):
        if isinstance(filters.warehouse, str):
            filters.warehouse = [filters.warehouse]
        
        for wh in filters.warehouse:
            if not frappe.db.exists("Warehouse", wh):
                frappe.throw(_("Warehouse {0} does not exist").format(wh))
    
    # Validate item group if provided
    if filters.get("item_group") and not frappe.db.exists("Item Group", filters.item_group):
        frappe.throw(_("Item Group {0} does not exist").format(filters.item_group))
    
    # Validate brand if provided
    if filters.get("brand") and not frappe.db.exists("Brand", filters.brand):
        frappe.throw(_("Brand {0} does not exist").format(filters.brand))
    
    # Validate voucher type if provided
    if filters.get("voucher_type") and not frappe.db.exists("DocType", filters.voucher_type):
        frappe.throw(_("Voucher Type {0} does not exist").format(filters.voucher_type))
    
    # Validate batch no if provided
    if filters.get("batch_no") and not frappe.db.exists("Batch", filters.batch_no):
        frappe.throw(_("Batch {0} does not exist").format(filters.batch_no))


def get_columns():
    """Define report columns with proper formatting"""
    return [
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "label": _("Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 140
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 140
        },
        {
            "label": _("Batch"),
            "fieldname": "batch_no",
            "fieldtype": "Link",
            "options": "Batch",
            "width": 120
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 160
        },
        {
            "label": _("UOM"),
            "fieldname": "uom",
            "fieldtype": "Data",
            "width": 80
        },
        {
            "label": _("FAT %"),
            "fieldname": "fat_per",
            "fieldtype": "Float",
            "width": 80,
            "precision": 3
        },
        {
            "label": _("FAT (Kg)"),
            "fieldname": "fat",
            "fieldtype": "Float",
            "width": 80,
            "precision": 3
        },
        {
            "label": _("SNF %"),
            "fieldname": "snf_per",
            "fieldtype": "Float",
            "width": 80,
            "precision": 3
        },
        {
            "label": _("SNF (Kg)"),
            "fieldname": "snf",
            "fieldtype": "Float",
            "width": 80,
            "precision": 3
        },
        {
            "label": _("Qty (L)"),
            "fieldname": "qty_in_liter",
            "fieldtype": "Float",
            "width": 110,
            "precision": 3
        },
        {
            "label": _("Qty After Transaction (L)"),
            "fieldname": "qty_after_transaction_in_liter",
            "fieldtype": "Float",
            "width": 190,
            "precision": 3
        },
        {
            "label": _("Qty (Kg)"),
            "fieldname": "qty_in_kg",
            "fieldtype": "Float",
            "width": 110,
            "precision": 3
        },
        {
            "label": _("Qty After Transaction (Kg)"),
            "fieldname": "qty_after_transaction_in_kg",
            "fieldtype": "Float",
            "width": 210,
            "precision": 3
        },
    ]


def get_entries(filters):
    """Fetch ledger entries based on filters with proper error handling"""
    try:
        MQLE = DocType("Milk Quality Ledger Entry")
        Item = DocType("Item")
        
        # Build base query with LEFT JOIN to handle items without names
        query = (
            frappe.qb.from_(MQLE)
            .left_join(Item).on(Item.name == MQLE.item_code)
            .select(
                MQLE.posting_date,
                Coalesce(MQLE.posting_time, "00:00:00").as_("posting_time"),
                MQLE.item_code,
                Coalesce(Item.item_name, MQLE.item_code).as_("item_name"),
                MQLE.warehouse,
                MQLE.batch_no,
                MQLE.voucher_type,
                MQLE.voucher_no,
                Coalesce(MQLE.uom, "").as_("uom"),
                Coalesce(MQLE.qty_in_liter, 0).as_("qty_in_liter"),
                Coalesce(MQLE.qty_after_transaction_in_liter, 0).as_("qty_after_transaction_in_liter"),
                Coalesce(MQLE.qty_in_kg, 0).as_("qty_in_kg"),
                Coalesce(MQLE.qty_after_transaction_in_kg, 0).as_("qty_after_transaction_in_kg"),
                Coalesce(MQLE.fat_per, 0).as_("fat_per"),
                Coalesce(MQLE.fat, 0).as_("fat"),
                Coalesce(MQLE.snf_per, 0).as_("snf_per"),
                Coalesce(MQLE.snf, 0).as_("snf"),
                Coalesce(Item.stock_uom, "").as_("stock_uom"),
            )
            .where(
                (MQLE.company == filters.company)
                & (MQLE.is_cancelled == 0)
                & (MQLE.posting_date >= filters.from_date)
                & (MQLE.posting_date <= filters.to_date)
            )
            .orderby(MQLE.posting_date)
            .orderby(MQLE.posting_time)
            .orderby(MQLE.creation)
        )
        
        # Apply optional filters
        if filters.get("item_code"):
            item_codes = filters.item_code if isinstance(filters.item_code, list) else [filters.item_code]
            query = query.where(MQLE.item_code.isin(item_codes))
        
        if filters.get("warehouse"):
            warehouses = filters.warehouse if isinstance(filters.warehouse, list) else [filters.warehouse]
            query = query.where(MQLE.warehouse.isin(warehouses))
        
        if filters.get("item_group"):
            query = query.where(Item.item_group == filters.item_group)
        
        if filters.get("brand"):
            query = query.where(Item.brand == filters.brand)
        
        if filters.get("voucher_type"):
            query = query.where(MQLE.voucher_type == filters.voucher_type)
        
        if filters.get("voucher_no"):
            query = query.where(MQLE.voucher_no == filters.voucher_no)
        
        if filters.get("batch_no"):
            query = query.where(MQLE.batch_no == filters.batch_no)
        
        return query.run(as_dict=True)
    
    except Exception as e:
        frappe.log_error(
            message=frappe.get_traceback(),
            title="Milk Quality Ledger Report Error"
        )
        frappe.throw(_("Error fetching ledger entries: {0}").format(str(e)))


def build_row(e, filters):
    """Build a single row with proper null handling and formatting"""
    try:
        # Handle posting time with fallback
        posting_time = e.get("posting_time") or "00:00:00"
        posting_date = e.get("posting_date")
        
        # Safely construct datetime
        if posting_date:
            try:
                date = get_datetime(f"{posting_date} {posting_time}")
            except Exception:
                date = get_datetime(posting_date)
        else:
            date = None
        
        # Determine UOM to display
        include_uom = cint(filters.get("include_uom"))
        if include_uom and e.get("stock_uom"):
            uom = e.get("stock_uom")
        else:
            uom = e.get("uom") or ""
        
        return {
            "date": date,
            "item_code": e.get("item_code") or "",
            "item_name": e.get("item_name") or "",
            "warehouse": e.get("warehouse") or "",
            "batch_no": e.get("batch_no") or "",
            "voucher_type": e.get("voucher_type") or "",
            "voucher_no": e.get("voucher_no") or "",
            "uom": uom,
            "qty_in_liter": flt(e.get("qty_in_liter", 0), 3),
            "qty_after_transaction_in_liter": flt(e.get("qty_after_transaction_in_liter", 0), 3),
            "qty_in_kg": flt(e.get("qty_in_kg", 0), 3),
            "qty_after_transaction_in_kg": flt(e.get("qty_after_transaction_in_kg", 0), 3),
            "fat_per": flt(e.get("fat_per", 0), 3),
            "fat": flt(e.get("fat", 0), 3),
            "snf_per": flt(e.get("snf_per", 0), 3),
            "snf": flt(e.get("snf", 0), 3),
        }
    
    except Exception as ex:
        frappe.log_error(
            message=f"Error building row: {frappe.get_traceback()}",
            title="Milk Quality Ledger Row Build Error"
        )
        # Return a row with safe defaults
        return {
            "date": None,
            "item_code": e.get("item_code", ""),
            "item_name": e.get("item_name", ""),
            "warehouse": "",
            "batch_no": "",
            "voucher_type": "",
            "voucher_no": "",
            "uom": "",
            "qty_in_liter": 0.0,
            "qty_after_transaction_in_liter": 0.0,
            "qty_in_kg": 0.0,
            "qty_after_transaction_in_kg": 0.0,
            "fat_per": 0.0,
            "fat": 0.0,
            "snf_per": 0.0,
            "snf": 0.0,
        }
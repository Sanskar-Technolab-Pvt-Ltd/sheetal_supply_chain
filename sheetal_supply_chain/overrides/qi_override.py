import frappe
import json
from frappe.utils import flt
from frappe import _
from erpnext.controllers.stock_controller import make_quality_inspections as erp_make_qi


@frappe.whitelist()
def make_quality_inspections(doctype, docname, items, inspection_type):
    """
    Custom behavior:
    - Purchase Receipt → add custom_warehouse
    - Stock Entry → force inspection_type = "In Process"
    - All others → default ERPNext logic
    """

    # -------------------------
    # CASE 1: STOCK ENTRY
    # -------------------------
    if doctype == "Stock Entry":
        inspection_type = "In Process"   # force override

        if isinstance(items, str):
            items = json.loads(items)
            
                # Fetch Stock Entry doc to read finished item warehouse
        se_doc = frappe.get_doc("Stock Entry", docname)

        # Identify finished item row → warehouse = t_warehouse
        finished_item_warehouse = None
        for row in se_doc.items:
            if row.is_finished_item:
                finished_item_warehouse = row.t_warehouse
                break
            
            
        inspections = []
        for item in items:

            qi_doc = {
                "doctype": "Quality Inspection",
                "inspection_type": inspection_type,   # forced
                "inspected_by": frappe.session.user,
                "reference_type": doctype,
                "reference_name": docname,
                "item_code": item.get("item_code"),
                "description": item.get("description"),
                "sample_size": flt(item.get("sample_size")),
                "item_serial_no": item.get("serial_no").split("\n")[0] if item.get("serial_no") else None,
                "batch_no": item.get("batch_no"),
                "child_row_reference": item.get("child_row_reference"),
                "custom_warehouse": finished_item_warehouse,
            }

            qi = frappe.get_doc(qi_doc)
            qi.save()
            inspections.append(qi.name)

        return inspections

    # -------------------------
    #  CASE 2: PURCHASE RECEIPT
    # -------------------------
    if doctype == "Purchase Receipt":
        if isinstance(items, str):
            items = json.loads(items)

        # get full PR doc
        pr_doc = frappe.get_doc("Purchase Receipt", docname)

        inspections = []
        for item in items:

            if flt(item.get("sample_size")) > flt(item.get("qty")):
                frappe.throw(
                    _("{item_name}'s Sample Size ({sample_size}) cannot be greater than the Accepted Quantity ({accepted_quantity})").format(
                        item_name=item.get("item_name"),
                        sample_size=item.get("sample_size"),
                        accepted_quantity=item.get("qty"),
                    )
                )

            # find warehouse using child_row_reference → PR Item name
            warehouse = None
            if item.get("child_row_reference"):
                for pr_item in pr_doc.items:
                    if pr_item.name == item.get("child_row_reference"):
                        warehouse = pr_item.warehouse
                        break

            qi_doc = {
                "doctype": "Quality Inspection",
                "inspection_type": inspection_type,
                "inspected_by": frappe.session.user,
                "reference_type": doctype,
                "reference_name": docname,
                "item_code": item.get("item_code"),
                "description": item.get("description"),
                "sample_size": flt(item.get("sample_size")),
                "item_serial_no": item.get("serial_no").split("\n")[0] if item.get("serial_no") else None,
                "batch_no": item.get("batch_no"),
                "child_row_reference": item.get("child_row_reference"),
                "custom_warehouse": warehouse,   
                "custom_supplier_code": pr_doc.custom_supplier_code,  

            }

            qi = frappe.get_doc(qi_doc)
            qi.save()
            inspections.append(qi.name)

        return inspections

    # -------------------------
    #  CASE 3: ALL OTHER DOCTYPES → USE DEFAULT
    # -------------------------
    return erp_make_qi(doctype, docname, items, inspection_type)

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



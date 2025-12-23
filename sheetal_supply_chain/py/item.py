import frappe
import re

def make_abbr(name):

    if not name:
        return ""

    words = re.split(r"\s+", name.strip())
    abbr = ""

    for word in words:
        # Find first alphabet character in the word
        match = re.search(r"[A-Za-z]", word)
        if match:
            abbr += match.group(0).upper()

    return abbr



def set_item_series(doc, method=None):
    if not doc.item_group:
        frappe.throw("Item Group is required to generate Item Code")

    # Child Item Group
    item_group = frappe.get_doc("Item Group", doc.item_group)
    item_group_abbr = make_abbr(item_group.name)

    # Parent Item Group
    if not item_group.parent_item_group:
        frappe.throw(f"Parent Item Group not set for {item_group.name}")

    parent_group = frappe.get_doc("Item Group", item_group.parent_item_group)
    parent_group_abbr = make_abbr(parent_group.name)

    if not parent_group_abbr or not item_group_abbr:
        frappe.throw("Unable to generate abbreviation from Item Group")

    prefix = f"{parent_group_abbr}-{item_group_abbr}"

    # Get last item in this series
    last_item = frappe.db.sql(
        """
        SELECT name FROM `tabItem`
        WHERE name LIKE %s
        ORDER BY name DESC
        LIMIT 1
        """,
        (prefix + "-%",),
        as_dict=True,
    )

    if last_item:
        last_no = int(last_item[0]["name"].split("-")[-1])
        new_no = last_no + 1
    else:
        new_no = 1

    doc.name = f"{prefix}-{str(new_no).zfill(4)}"

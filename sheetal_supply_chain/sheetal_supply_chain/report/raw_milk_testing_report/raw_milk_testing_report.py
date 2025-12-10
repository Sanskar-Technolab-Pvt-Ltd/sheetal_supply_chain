# # # Copyright (c) 2025, Sanskar Technolab Pvt Ltd and contributors
# # # For license information, please see license.txt

# # # import frappe
# # from frappe import _


# # def execute(filters: dict | None = None):
# # 	"""Return columns and data for the report.

# # 	This is the main entry point for the report. It accepts the filters as a
# # 	dictionary and should return columns and data. It is called by the framework
# # 	every time the report is refreshed or a filter is updated.
# # 	"""
# # 	columns = get_columns()
# # 	data = get_data()

# # 	return columns, data


# # def get_columns() -> list[dict]:
# # 	"""Return columns for the report.

# # 	One field definition per column, just like a DocType field definition.
# # 	"""
# # 	return [
# # 		{
# # 			"label": _("Column 1"),
# # 			"fieldname": "column_1",
# # 			"fieldtype": "Data",
# # 		},
# # 		{
# # 			"label": _("Column 2"),
# # 			"fieldname": "column_2",
# # 			"fieldtype": "Int",
# # 		},
# # 	]


# # def get_data() -> list[list]:
# # 	"""Return data for the report.

# # 	The report data is a list of rows, with each row being a list of cell values.
# # 	"""
# # 	return [
# # 		["Row 1", 1],
# # 		["Row 2", 2],
# # 	]


# import frappe

# def execute(filters=None):
#     columns = get_columns()
#     data = get_data(filters)
#     return columns, data


# def get_columns():
#     return [
#         {"label": "QI ID", "fieldname": "qi_id", "fieldtype": "Link", "options": "Quality Inspection"},
#         {"label": "Purchase Receipt", "fieldname": "pr_id", "fieldtype": "Link", "options": "Purchase Receipt"},
#         {"label": "Tanker No", "fieldname": "tanker_no", "fieldtype": "Data"},
#         {"label": "Supplier Name", "fieldname": "supplier", "fieldtype": "Data"},
#         {"label": "In Time", "fieldname": "in_time", "fieldtype": "Data"},
#         {"label": "Out Time", "fieldname": "out_time", "fieldtype": "Data"},
#         {"label": "Net Weight", "fieldname": "net_weight", "fieldtype": "Float"},

#         # Parameter columns
#         {"label": "Temp", "fieldname": "temp", "fieldtype": "Data"},
#         {"label": "Fat", "fieldname": "fat", "fieldtype": "Data"},
#         {"label": "LR", "fieldname": "lr", "fieldtype": "Data"},
#         {"label": "SNF", "fieldname": "snf", "fieldtype": "Data"},
#         {"label": "Alcohol", "fieldname": "alcohol", "fieldtype": "Data"},
#         {"label": "Acidity", "fieldname": "acidity", "fieldtype": "Data"},
#         {"label": "Ammonia", "fieldname": "ammonia", "fieldtype": "Data"},
#         {"label": "MBRT", "fieldname": "mbrt", "fieldtype": "Data"},
#         {"label": "Sucrose", "fieldname": "sucrose", "fieldtype": "Data"},
#         {"label": "Starch", "fieldname": "starch", "fieldtype": "Data"},
#         {"label": "Neutralizer", "fieldname": "neutralizer", "fieldtype": "Data"},
#         {"label": "Detergent", "fieldname": "detergent", "fieldtype": "Data"},
#         {"label": "Urea", "fieldname": "urea", "fieldtype": "Data"},
#         {"label": "Maltose", "fieldname": "maltose", "fieldtype": "Data"},
#         {"label": "BR", "fieldname": "br", "fieldtype": "Data"},
#         {"label": "RM", "fieldname": "rm", "fieldtype": "Data"},
#         {"label": "Wash RM", "fieldname": "wash_rm", "fieldtype": "Data"},
#         {"label": "Channa", "fieldname": "channa", "fieldtype": "Data"},

#         {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data"},
#     ]


# def get_data(filters):
#     # Fetch all quality inspections between dates
#     qi_list = frappe.get_all(
#         "Quality Inspection",
#         filters={"report_date": ["between", [filters.from_date, filters.to_date]]},
#         fields=["name", "reference_name", "custom_in_time", "custom_out_time", "remarks"]
#     )

#     data = []

#     for qi in qi_list:
#         row = {
#             "qi_id": qi.name,
#             "in_time": qi.custom_in_time,
#             "out_time": qi.custom_out_time,
#             "remarks": qi.remarks
#         }

#         # ------------------------
#         # 1. Get Purchase Receipt
#         # ------------------------
#         if qi.reference_name:
#             pr = frappe.db.get_value(
#                 "Purchase Receipt",
#                 qi.reference_name,
#                 ["name", "custom_tanker_no", "supplier", "custom_net_weight"],
#                 as_dict=True
#             )

#             if pr:
#                 row.update({
#                     "pr_id": pr.name,
#                     "tanker_no": pr.custom_tanker_no,
#                     "supplier": pr.supplier,
#                     "net_weight": pr.custom_net_weight
#                 })

#         # ------------------------
#         # 2. Get QI Readings Child Table
#         # ------------------------
#         readings = frappe.get_all(
#             "Quality Inspection Reading",
#             filters={"parent": qi.name},
#             fields=["specification", "reading_1", "reading_value"]
#         )

#         # Map readings by specification field
#         row.update(extract_parameters(readings))

#         data.append(row)

#     return data


# def extract_parameters(readings):
#     # Mapping specification -> column fieldname
#     param_map = {
#         "Temp": "temp",
#         "Fat": "fat",
#         "LR": "lr",
#         "SNF": "snf",
#         "Alcohol": "alcohol",
#         "Acidity": "acidity",
#         "Ammonia": "ammonia",
#         "MBRT": "mbrt",
#         "Sucrose": "sucrose",
#         "Starch": "starch",
#         "Neutralizer": "neutralizer",
#         "Detergent": "detergent",
#         "Urea": "urea",
#         "Maltose": "maltose",
#         "BR": "br",
#         "RM": "rm",
#         "Wash RM": "wash_rm",
#         "Channa": "channa",
#     }

#     result = {v: "" for v in param_map.values()}

#     for r in readings:
#         if r.specification in param_map:
#             col = param_map[r.specification]
#             value = r.reading_1 or r.reading_value or ""
#             result[col] = value

#     return result


import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "QI ID", "fieldname": "qi_id", "fieldtype": "Link", "options": "Quality Inspection"},
        {"label": "Purchase Receipt", "fieldname": "pr_id", "fieldtype": "Link", "options": "Purchase Receipt"},
        {"label": "Tanker No", "fieldname": "tanker_no", "fieldtype": "Data"},
        {"label": "Supplier Name", "fieldname": "supplier", "fieldtype": "Data"},
        {"label": "In Time", "fieldname": "in_time", "fieldtype": "Data"},
        {"label": "Out Time", "fieldname": "out_time", "fieldtype": "Data"},
        {"label": "Net Weight", "fieldname": "net_weight", "fieldtype": "Float"},

        # Parameter columns
        {"label": "Temp", "fieldname": "temp", "fieldtype": "Data"},
        {"label": "Fat", "fieldname": "fat", "fieldtype": "Data"},
        {"label": "LR", "fieldname": "lr", "fieldtype": "Data"},
        {"label": "SNF", "fieldname": "snf", "fieldtype": "Data"},
        {"label": "Alcohol", "fieldname": "alcohol", "fieldtype": "Data"},
        {"label": "Acidity", "fieldname": "acidity", "fieldtype": "Data"},
        {"label": "Ammonia", "fieldname": "ammonia", "fieldtype": "Data"},
        {"label": "MBRT", "fieldname": "mbrt", "fieldtype": "Data"},
        {"label": "Sucrose", "fieldname": "sucrose", "fieldtype": "Data"},
        {"label": "Starch", "fieldname": "starch", "fieldtype": "Data"},
        {"label": "Neutralizer", "fieldname": "neutralizer", "fieldtype": "Data"},
        {"label": "Detergent", "fieldname": "detergent", "fieldtype": "Data"},
        {"label": "Urea", "fieldname": "urea", "fieldtype": "Data"},
        {"label": "Maltose", "fieldname": "maltose", "fieldtype": "Data"},
        {"label": "BR", "fieldname": "br", "fieldtype": "Data"},
        {"label": "RM", "fieldname": "rm", "fieldtype": "Data"},
        {"label": "Wash RM", "fieldname": "wash_rm", "fieldtype": "Data"},
        {"label": "Channa", "fieldname": "channa", "fieldtype": "Data"},

        {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data"},
    ]


def get_data(filters):
    # Base filter: Only submitted QI
    qi_filters = {
        "docstatus": 1,  # submitted
        "report_date": ["between", [filters.from_date, filters.to_date]]
    }

    # Additional Filters
    if filters.get("quality_inspection"):
        qi_filters["name"] = filters.quality_inspection

    if filters.get("purchase_receipt"):
        qi_filters["reference_name"] = filters.purchase_receipt

    # Supplier filter will apply after PR fetch

    qi_list = frappe.get_all(
        "Quality Inspection",
        filters=qi_filters,
        fields=["name", "reference_name", "custom_in_time", "custom_out_time", "remarks"]
    )

    data = []

    for qi in qi_list:
        row = {
            "qi_id": qi.name,
            "in_time": qi.custom_in_time,
            "out_time": qi.custom_out_time,
            "remarks": qi.remarks
        }

        # Purchase Receipt details
        pr = None
        if qi.reference_name:
            pr = frappe.db.get_value(
                "Purchase Receipt",
                qi.reference_name,
                ["name", "custom_tanker_no", "supplier", "custom_net_weight"],
                as_dict=True
            )

        # If supplier filter applied, skip mismatch
        if filters.get("supplier") and (not pr or pr.supplier != filters.supplier):
            continue

        if pr:
            row.update({
                "pr_id": pr.name,
                "tanker_no": pr.custom_tanker_no,
                "supplier": pr.supplier,
                "net_weight": pr.custom_net_weight
            })

        # QI Readings
        readings = frappe.get_all(
            "Quality Inspection Reading",
            filters={"parent": qi.name},
            fields=["specification", "reading_1", "reading_value"]
        )

        row.update(extract_parameters(readings))
        data.append(row)

    return data


def extract_parameters(readings):
    param_map = {
        "Temp": "temp",
        "Fat": "fat",
        "LR": "lr",
        "SNF": "snf",
        "Alcohol": "alcohol",
        "Acidity": "acidity",
        "Ammonia": "ammonia",
        "MBRT": "mbrt",
        "Sucrose": "sucrose",
        "Starch": "starch",
        "Neutralizer": "neutralizer",
        "Detergent": "detergent",
        "Urea": "urea",
        "Maltose": "maltose",
        "BR": "br",
        "RM": "rm",
        "Wash RM": "wash_rm",
        "Channa": "channa",
    }

    result = {v: "" for v in param_map.values()}

    for r in readings:
        if r.specification in param_map:
            col = param_map[r.specification]
            value = r.reading_1 or r.reading_value or ""
            result[col] = value

    return result


// Copyright (c) 2025, Sanskar Technolab Pvt Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Raw Milk Testing Report"] = {
    "filters": [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "quality_inspection",
            label: "Quality Inspection",
            fieldtype: "Link",
            options: "Quality Inspection",
            get_query: function() {
                return {
                    filters: {
                        docstatus: 1 
                    }
                };
            }
        },
        {
            fieldname: "purchase_receipt",
            label: "Purchase Receipt",
            fieldtype: "Link",
            options: "Purchase Receipt"
        },
        {
            fieldname: "supplier",
            label: "Supplier",
            fieldtype: "Link",
            options: "Supplier"
        },
    ]
};

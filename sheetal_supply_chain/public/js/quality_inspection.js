frappe.ui.form.on("Quality Inspection", {
    refresh(frm) {
        // for filtering only draft PR records

        frm.set_query("reference_name", function() {
            return {
                filters: {
                    docstatus: 0,             
                    company: frm.doc.company
                }
            };
        });

    },

 
});


frappe.ui.form.on("Quality Inspection Reading", {
    status(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        // Apply only when is_numeric is disabled (0)
        if (!row.numeric) {

            if (row.status === "Accepted") {
                row.reading_value = "Ok";
            }
            else if (row.status === "Rejected") {
                row.reading_value = "Not Ok";
            }
            else {
                row.reading_value = "";
            }

            frm.refresh_field("readings");
        }
    },
    numeric(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        if (row.numeric) {
            // Numeric enabled → reset reading_value
            row.reading_value = "";
        } else {
            // Numeric disabled → update according to status
            if (row.status === "Accepted") {
                row.reading_value = "Ok";
            } 
            else if (row.status === "Rejected") {
                row.reading_value = "Not Ok";
            } 
            else {
                row.reading_value = "";
            }
        }

        frm.refresh_field("readings");
    },
});

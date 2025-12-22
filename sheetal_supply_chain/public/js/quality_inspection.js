frappe.ui.form.on("Quality Inspection", {
    //! Filter reference documents to show only draft records of the selected company
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

    //! Apply warehouse-based item filtering only when inspection type is set to Internal
    inspection_type(frm) {

        // Leave original 3 types untouched
        if (["Incoming", "Outgoing", "In Process"].includes(frm.doc.inspection_type)) {
            return;
        }

        // New behaviour for "Internal"
        if (frm.doc.inspection_type === "Internal") {

            frm.set_query("item_code", function() {
                return {
                    query: "sheetal_supply_chain.api.warehouse_items.get_items_from_warehouse",
                    filters: {
                        warehouse: frm.doc.custom_warehouse || ""
                    }
                };
            });
        }
    },

    //! Reapply item filtering when warehouse changes for Internal Quality Inspections
    custom_warehouse(frm) {
        if (frm.doc.inspection_type === "Internal") {

            frm.set_query("item_code", function() {
                return {
                    query: "sheetal_supply_chain.py.quality_inspection.get_items_from_warehouse",
                    filters: {
                        warehouse: frm.doc.custom_warehouse || ""
                    }
                };
            });

            // Optional: auto-clear previous value
            // frm.set_value("item_code", "");
        }
    },

    item_code(frm) {
        // Covers manual item selection
        fetch_mbrt_from_item(frm);
    },
    onload(frm) {
        // Covers auto-created QI (PR / SE)
        setTimeout(() => {
            fetch_mbrt_from_item(frm);
        }, 300);
    },

    custom_mbrt_start_time(frm) {
        calculate_total_time(frm);
    },
    custom_mbrt_end_time(frm) {
        calculate_total_time(frm);
    }



 
});

//! Handle status and numeric-based behavior for Quality Inspection Reading child table
frappe.ui.form.on("Quality Inspection Reading", {

    //! Set reading_value automatically based on Accepted/Rejected status for non-numeric readings
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

    //! Reset or derive reading_value when numeric flag is toggled in Quality Inspection Reading
    numeric(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        if (row.numeric) {
            // Numeric enabled → reset reading_value
            row.reading_value = "";
            row.manual_inspection = 0
        } else {
            row.manual_inspection = 1
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



function fetch_mbrt_from_item(frm) {
    // Safety checks
    if (!frm.doc.item_code) return;

    // Do NOT override if user already changed it
    if (frm.doc.__mbrt_fetched) return;

    frappe.db.get_value(
        'Item',
        frm.doc.item_code,
        'custom_has_mbrt_required',
        (r) => {
            if (r && r.custom_has_mbrt_required !== undefined) {
                frm.set_value(
                    'custom_has_mbrt_required',
                    r.custom_has_mbrt_required
                );

                // Mark as fetched once
                frm.doc.__mbrt_fetched = true;
            }
        }
    );
}


function calculate_total_time(frm) {
    if (frm.doc.custom_mbrt_start_time && frm.doc.custom_mbrt_end_time) {

        let start = frappe.datetime.str_to_obj(frm.doc.custom_mbrt_start_time);
        let end = frappe.datetime.str_to_obj(frm.doc.custom_mbrt_end_time);

        let diff_ms = end - start;

        if (diff_ms < 0) {
            frm.set_value('custom_total_mbrt_time', '');
            frappe.msgprint(__('End Time cannot be before Start Time'));
            return;
        }

        // Duration expects SECONDS
        let total_seconds = diff_ms / 1000;

        frm.set_value('custom_total_mbrt_time', total_seconds);
    }
}

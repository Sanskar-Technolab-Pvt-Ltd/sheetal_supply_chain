//! Handle Quality Inspection form behavior including reference filtering and warehouse-based item selection
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

 
        // frm.set_query("item_code", function(doc) {
        //     if (!doc.custom_warehouse) {
        //         return {
        //             filters: {
        //                 name: ["is", "set", ""]
        //             }
        //         };
        //     }

        //     return {
        //         query: "sheetal_supply_chain.py.quality_inspection.get_items_with_stock",
        //         filters: {
        //             warehouse: doc.custom_warehouse
        //         }
        //     };
        // });
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
    }

    // custom_warehouse(frm) {
    //     frm.set_value("item_code", "");
    //     frm.refresh_field("item_code");
    // }

 
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


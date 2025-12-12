frappe.ui.form.on("Purchase Receipt", {
    custom_second_weight(frm) {
        let first = flt(frm.doc.custom_first_weight);
        let second = flt(frm.doc.custom_second_weight);

        frm.set_value("custom_net_weight", first - second);
        frm.set_value("custom_net_weight_litre", frm.doc.custom_net_weight / 1.034);


    },

    custom_first_weight(frm) {
        let first = flt(frm.doc.custom_first_weight);
        let second = flt(frm.doc.custom_second_weight);

        // Recalculate if second weight exists
        if (second) {
            frm.set_value("custom_net_weight", first - second);
            
        }
    },


    refresh(frm) {
        // Update all items with QI on form load
        frm.doc.items.forEach(item => {
            if (item.quality_inspection) {
                fetch_fat_snf(frm, item.doctype, item.name);
            }
        });

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button("Milk Ledger", function () {
                open_milk_quality_ledger(frm);  
            }, __("View"));
        }
        
    },
    onload(frm) {
        if (frm.doc.__islocal) return; // Skip for new documents
        frm.doc.items.forEach(item => {
            if (item.quality_inspection) {
                fetch_fat_snf(frm, item.doctype, item.name);
            }
        });
    }

});



frappe.ui.form.on("Purchase Receipt Item", {

    quality_inspection(frm, cdt, cdn) {
        fetch_fat_snf(frm, cdt, cdn);
    },
    form_render(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.quality_inspection) {
            fetch_fat_snf(frm, cdt, cdn);
        }
    }

});



 
function fetch_fat_snf(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (!row.quality_inspection) {
        frappe.model.set_value(cdt, cdn, "custom_fat", 0);
        frappe.model.set_value(cdt, cdn, "custom_snf", 0);
        frappe.model.set_value(cdt, cdn, "custom_fat_kg", 0);
        frappe.model.set_value(cdt, cdn, "custom_snf_kg", 0);
        return;
    }
    frappe.call({
        method: "sheetal_supply_chain.py.purchase_receipt.update_fat_snf_js",
        args: {
            qi: row.quality_inspection,
            stock_qty: row.stock_qty
        },
        freeze: true,
        freeze_message: __("Fetching QI readings..."),

        callback(r) {
            if (!r.message) return;
        
            // Fix rounding issues (VERY IMPORTANT)
            let fat = flt(r.message.fat, 3);
            let snf = flt(r.message.snf, 3);
            let fat_kg = flt(r.message.fat_kg, 3);
            let snf_kg = flt(r.message.snf_kg, 3);
        
            frappe.model.set_value(cdt, cdn, "custom_fat", fat);
            frappe.model.set_value(cdt, cdn, "custom_snf", snf);
            frappe.model.set_value(cdt, cdn, "custom_fat_kg", fat_kg);
            frappe.model.set_value(cdt, cdn, "custom_snf_kg", snf_kg);
        
            frm.refresh_field("items");
        }
        
    });
}
 

/**
 * Redirects user to Milk Quality Ledger with auto-filled filters
 * Safe for all edge cases
 */
function open_milk_quality_ledger(frm) {


    // -------- 2) Mandatory Fields --------
    if (!frm.doc.company) {
        frappe.msgprint("Company is missing. Cannot open Milk Ledger.");
        return;
    }

    if (!frm.doc.name) {
        frappe.msgprint("Document name not found.");
        return;
    }

    // -------- 3) Build Redirect URL (Manual + Safe) --------
    const base_url = window.location.origin;  

    let url = `${base_url}/desk/query-report/Milk%20Quality%20Ledger`
        + `?company=${encodeURIComponent(frm.doc.company)}`
        + `&from_date=${frm.doc.posting_date}`
        + `&to_date=${frm.doc.posting_date}`
        + `&voucher_type=${encodeURIComponent("Purchase Receipt")}`
        + `&voucher_no=${encodeURIComponent(frm.doc.name)}`;

    // -------- 4) Redirect --------
    window.location.href = url;
}

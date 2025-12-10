frappe.ui.form.on("Purchase Receipt", {
    custom_second_weight(frm) {
        let first = flt(frm.doc.custom_first_weight);
        let second = flt(frm.doc.custom_second_weight);

        frm.set_value("custom_net_weight", first - second);
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
            frappe.model.set_value(cdt, cdn, "custom_fat", r.message.fat);
            frappe.model.set_value(cdt, cdn, "custom_snf", r.message.snf);
            frappe.model.set_value(cdt, cdn, "custom_fat_kg", r.message.fat_kg);
            frappe.model.set_value(cdt, cdn, "custom_snf_kg", r.message.snf_kg);
            frm.refresh_field("items");
        }
    });
}
 

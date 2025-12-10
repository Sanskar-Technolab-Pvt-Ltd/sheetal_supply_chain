frappe.ui.form.on("Stock Entry Detail", {

    quality_inspection(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Run ONLY for finished items
        if (row.is_finished_item == 1) {
            fetch_fat_snf_stock_entry(frm, cdt, cdn);
        }
    },

    form_render(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.is_finished_item == 1 && row.quality_inspection) {
            fetch_fat_snf_stock_entry(frm, cdt, cdn);
        }
    }
});


frappe.ui.form.on("Stock Entry", {

    refresh(frm) {
        frm.doc.items.forEach(item => {
            if (item.is_finished_item == 1 && item.quality_inspection) {
                fetch_fat_snf_stock_entry(frm, item.doctype, item.name);
            }
        });
    },

    onload(frm) {
        if (frm.doc.__islocal) return;

        frm.doc.items.forEach(item => {
            if (item.is_finished_item == 1 && item.quality_inspection) {
                fetch_fat_snf_stock_entry(frm, item.doctype, item.name);
            }
        });
    }
});


function fetch_fat_snf_stock_entry(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    // Only finished items allowed
    if (row.is_finished_item != 1) return;

    if (!row.quality_inspection) {
        frappe.model.set_value(cdt, cdn, "custom_fat", 0);
        frappe.model.set_value(cdt, cdn, "custom_snf", 0);
        frappe.model.set_value(cdt, cdn, "custom_fat_kg", 0);
        frappe.model.set_value(cdt, cdn, "custom_snf_kg", 0);
        return;
    }

    frappe.call({
        method: "sheetal_supply_chain.py.stock_entry.update_fat_snf_js",
        args: {
            qi: row.quality_inspection,
            qty: row.qty // IMPORTANT for Stock Entry
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

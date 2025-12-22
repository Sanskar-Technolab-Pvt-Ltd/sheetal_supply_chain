frappe.ui.form.on("Work Order Item", {
    required_qty(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_fat_snf_row(row);
        calculate_stock_entry_totals(frm);
        frm.refresh_field("required_items");
    },

    custom_fat(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_fat_snf_row(row);
        calculate_stock_entry_totals(frm);
        frm.refresh_field("required_items");
    },  

    custom_snf(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_fat_snf_row(row);
        calculate_stock_entry_totals(frm);
        frm.refresh_field("required_items");
    }
});

//! Calculate FAT and SNF quantities (KG) for a single Stock Entry item row
function calculate_fat_snf_row(row) {
    let qty = flt(row.required_qty) || 0;
    let fat = flt(row.custom_fat) || 0;
    let snf = flt(row.custom_snf) || 0;

    row.custom_fat_kg = 0;
    row.custom_snf_kg = 0;

    if (qty !== 0) {
        row.custom_fat_kg = (qty * fat) / 100;
        row.custom_snf_kg = (qty * snf) / 100;
    }
}

//! Calculate and set total quantity, FAT/SNF KG, and weighted FAT/SNF percentages on Stock Entry
function calculate_stock_entry_totals(frm) {
    let total_qty = 0;
    let total_fat_kg = 0;
    let total_snf_kg = 0;
    let total_fat_per = 0;
    let total_snf_per = 0;


    if (!frm.doc || !frm.doc.required_items) return;

    frm.doc.required_items.forEach(item => {
        total_qty += flt(item.required_qty) || 0;
        total_fat_kg += flt(item.custom_fat_kg) || 0;
        total_snf_kg += flt(item.custom_snf_kg) || 0;
        total_fat_per += flt(item.custom_fat) || 0;
        total_snf_per += flt(item.custom_snf) || 0;

    });

    frm.set_value("custom_total_quantity", total_qty);
    frm.set_value("custom_total_fat_kg", total_fat_kg);
    frm.set_value("custom_total_snf_kg", total_snf_kg);
    frm.set_value("custom_total_fat_percentage", total_fat_per);
    frm.set_value("custom_total_snf_percentage", total_snf_per);


    if (total_qty !== 0) {
        frm.set_value("custom_fat_percentage", (total_fat_kg / total_qty) * 100);
        frm.set_value("custom_snf_percentage", (total_snf_kg / total_qty) * 100);
    } else {
        frm.set_value("custom_fat_percentage", 0);
        frm.set_value("custom_snf_percentage", 0);
    }
}


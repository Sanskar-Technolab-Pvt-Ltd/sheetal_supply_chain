// ! Global Stock Entry Form Script
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
    },

    qty(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_fat_snf_row(row);
        calculate_stock_entry_totals(frm);
        frm.refresh_field("items");
    },

    // custom_fat(frm, cdt, cdn) {
    //     let row = locals[cdt][cdn];
    //     calculate_fat_snf_row(row);
    //     calculate_stock_entry_totals(frm);
    //     frm.refresh_field("items");
    // },  

    // custom_snf(frm, cdt, cdn) {
    //     let row = locals[cdt][cdn];
    //     calculate_fat_snf_row(row);
    //     calculate_stock_entry_totals(frm);
    //     frm.refresh_field("items");
    // }
});

// ! Global Stock Entry Form Script
frappe.ui.form.on("Stock Entry", {

    refresh(frm) {
        frm.doc.items.forEach(item => {
            if (item.is_finished_item == 1 && item.quality_inspection) {
                fetch_fat_snf_stock_entry(frm, item.doctype, item.name);
            }
        });


        if (frm.doc.docstatus === 1) {
            frm.add_custom_button("Milk Ledger", function () {
                open_milk_quality_ledger(frm);  
            }, __("View"));
        }

        // ! calculate Stock entry Total
        // calculate_stock_entry_totals(frm);
    },

    onload(frm) {
        if (frm.doc.__islocal) return;

        frm.doc.items.forEach(item => {
            if (item.is_finished_item == 1 && item.quality_inspection) {
                fetch_fat_snf_stock_entry(frm, item.doctype, item.name);
            }
        });
    },

    items_add(frm) {
        calculate_stock_entry_totals(frm);
    },
    items_remove(frm) {
        calculate_stock_entry_totals(frm);
    }
    
});

//! Fetch FAT and SNF values from server using Quality Inspection for a finished Stock Entry item
function fetch_fat_snf_stock_entry(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    // Only finished items allowed
    if (row.is_finished_item != 1) return;
    if (row.custom_fat != 0 || row.custom_fat_kg!= 0 || row.custom_fat_kg!= 0 || row.custom_snf_kg !=0 ) return;
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
/**
 * Redirects user to Milk Quality Ledger with auto-filled filters
 * Safe for all edge cases
 */
//! Redirect user to Milk Quality Ledger report with Stock Entry filters applied

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
        + `&voucher_type=${encodeURIComponent("Stock Entry")}`
        + `&voucher_no=${encodeURIComponent(frm.doc.name)}`;

    // -------- 4) Redirect --------
    window.location.href = url;
}
// frappe.ui.form.on("BOM Item", {
//     // qty(frm, cdt, cdn) {
//     //     recalculate_bom(frm);
//     // },
//     // custom_fat_kg(frm, cdt, cdn) {
//     //     recalculate_bom(frm);
//     // },
//     // custom_snf_kg(frm, cdt, cdn) {
//     //     recalculate_bom(frm);
//     // }
// });

//! Calculate FAT and SNF quantities (KG) for a single Stock Entry item row
function calculate_fat_snf_row(row) {
    let qty = flt(row.qty) || 0;
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

    if (!frm.doc || !frm.doc.items) return;

    frm.doc.items.forEach(item => {
        total_qty += flt(item.qty) || 0;
        total_fat_kg += flt(item.custom_fat_kg) || 0;
        total_snf_kg += flt(item.custom_snf_kg) || 0;
    });

    frm.set_value("custom_total_quantity", total_qty);
    frm.set_value("custom_total_fat_kg", total_fat_kg);
    frm.set_value("custom_total_snf_kg", total_snf_kg);

    if (total_qty !== 0) {
        frm.set_value("custom_fat_percentage", (total_fat_kg / total_qty) * 100);
        frm.set_value("custom_snf_percentage", (total_snf_kg / total_qty) * 100);
    } else {
        frm.set_value("custom_fat_percentage", 0);
        frm.set_value("custom_snf_percentage", 0);
    }
}

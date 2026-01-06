frappe.ui.form.on("Work Order", {
    production_item: function(frm) {
        if (frm.doc.production_item) {
            setTimeout(() => {
                fetch_primary_uom(frm);
                fetch_secondary_uom(frm);
                // fetch_primary_uom_qty(frm);
                fetch_primary_secondary_uom_qty(frm);

            }, 100);
        }
    },
    qty(frm) {
        fetch_primary_secondary_uom_qty(frm);

    },
    validate(frm) {
        fetch_primary_uom(frm);
        fetch_secondary_uom(frm);
        // fetch_primary_uom_qty(frm);
        fetch_primary_secondary_uom_qty(frm);

    },
    onload(frm) {
        if (!frm.doc.custom_posting_date) {
            frm.set_value(
                "custom_posting_date",
                frappe.datetime.now_date()
            );
        }
    },
    custom_print_qr_button_for_primary_uom: function (frm) {

        // Safety check
        if (!frm.doc.custom_primary_uom) {
            frappe.msgprint(__('Primary UOM is not set'));
            return;
        }

        let d = new frappe.ui.Dialog({
            title: __('Print QR – Primary UOM'),
            fields: [
                {
                    fieldname: 'primary_uom',
                    fieldtype: 'Link',
                    label: __('Primary UOM'),
                    options: 'UOM',
                    default: frm.doc.custom_primary_uom,
                    read_only: 1
                },
                {
                    fieldname: 'primary_uom_qty',
                    fieldtype: 'Float',
                    label: __('Qty to Print'),
                    // default fetched from custom_primary_uom_qty
                    default: frm.doc.custom_primary_uom_qty || 0,
                    reqd: 1
                }
            ],
            primary_action_label: __('Print'),
            primary_action(values) {

                frm.set_value(
                    'custom_printed_qty_for_primary_uom',
                    values.primary_uom_qty
                ).then(() => {
                    // Auto-save the document
                    frm.save();
                });

                d.hide();
            }
        });

        d.show();
    },

    custom_print_qr_button_for_secondary_uom: function (frm) {

        if (!frm.doc.custom_secondary_uom) {
            frappe.msgprint(__('Secondary UOM is not set'));
            return;
        }

        let d = new frappe.ui.Dialog({
            title: __('Print QR – Secondary UOM'),
            fields: [
                {
                    fieldname: 'secondary_uom',
                    fieldtype: 'Link',
                    label: __('Secondary UOM'),
                    options: 'UOM',
                    default: frm.doc.custom_secondary_uom,
                    read_only: 1
                },
                {
                    fieldname: 'secondary_uom_qty',
                    fieldtype: 'Int',
                    label: __('Qty to Print'),
                    default: frm.doc.custom_secondary_uom_qty || 0,
                    reqd: 1
                }
            ],
            primary_action_label: __('Print'),
            primary_action(values) {

                if (values.secondary_uom_qty <= 0) {
                    frappe.msgprint(__('Qty must be greater than 0'));
                    return;
                }

                // Set printed qty in WO
                frm.set_value(
                    'custom_printed_qty_for_secondary_uom',
                    values.secondary_uom_qty
                ).then(() => {
                    // Auto-save the document
                    frm.save();
                });;

                // Call server to create Crate Master records
                frappe.call({
                    method: 'sheetal_supply_chain.py.work_order.create_crate_master_for_secondary_uom',
                    args: {
                        work_order: frm.doc.name,
                        qty: values.secondary_uom_qty
                    },
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.msgprint(__('Crate Master records created successfully'));
                        }
                    }
                });

                d.hide();
            }
        });

        d.show();
    }

});

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


// Fetches the Primary UOM from Item Master for the selected Production Item and sets it in the Work Order form


function fetch_primary_uom(frm) {
    if (!frm.doc.production_item) {
        frm.set_value("custom_primary_uom", "");
        return;
    }

    frappe.call({
        method: "sheetal_supply_chain.py.work_order.get_primary_uom_from_item",
        args: {
            item_code: frm.doc.production_item
        },
        callback: function (r) {
            if (r.message) {
                frm.set_value("custom_primary_uom", r.message);
            } else {
                frm.set_value("custom_primary_uom", "");
                frappe.msgprint(
                    __("No Primary UOM defined in Item Master for this item")
                );
            }
        }
    });
}


// Fetches the Secondary UOM from Item Master for the selected Production Item and sets it in the Work Order form
function fetch_secondary_uom(frm) {
    if (!frm.doc.production_item) {
        frm.set_value("custom_secondary_uom", "");
        return;
    }

    frappe.call({
        method: "sheetal_supply_chain.py.work_order.get_secondary_uom_from_item",
        args: {
            item_code: frm.doc.production_item
        },
        callback: function (r) {
            if (r.message) {
                frm.set_value("custom_secondary_uom", r.message);
            } else {
                frm.set_value("custom_secondary_uom", "");
                frappe.msgprint(
                    __("No Secondary UOM defined in Item Master for this item")
                );
            }
        }
    });
}


// Calculates and sets the Primary UOM quantity in the Work Order by converting the entered WO quantity using Item UOM conversion rules

// function fetch_primary_uom_qty(frm) {

//     if (!frm.doc.production_item || !frm.doc.qty) {
//         frm.set_value("custom_primary_uom_qty", 0);
//         return;
//     }

//     frappe.call({
//         method: "sheetal_supply_chain.py.work_order.get_primary_uom_qty",
//         args: {
//             item_code: frm.doc.production_item,
//             wo_qty: frm.doc.qty
//         },
//         callback: function (r) {
//             if (r.message !== undefined) {
//                 frm.set_value("custom_primary_uom_qty", r.message);
//             }
//         }
//     });
// }


// function fetch_secondary_uom_qty(frm) {
//     if (!frm.doc.production_item || !frm.doc.qty) {
//         frm.set_value("custom_secondary_uom_qty", 0);
//         return;
//     }

//     // Step 1: Fetch primary UOM qty from server
//     frappe.call({
//         method: "sheetal_supply_chain.py.work_order.get_primary_uom_qty",
//         args: {
//             item_code: frm.doc.production_item,
//             wo_qty: frm.doc.qty
//         },
//         callback: function (r_primary) {
//             let primary_qty = r_primary.message || 0;
//             console.log("Prinmary qty",primary_qty)
//             // Step 2: Calculate secondary UOM qty using server method
//             frappe.call({
//                 method: "sheetal_supply_chain.py.work_order.get_secondary_uom_qty",
//                 args: {
//                     item_code: frm.doc.production_item,
//                     primary_qty: primary_qty
//                 },
//                 callback: function (r_secondary) {
//                     if (r_secondary.message !== undefined) {
//                         frm.set_value("custom_secondary_uom_qty", r_secondary.message);

//                     }
//                 }
//             });
//         }
//     });
// }

function fetch_primary_secondary_uom_qty(frm) {
    if (!frm.doc.production_item || !frm.doc.qty) {
        frm.set_value("custom_primary_uom_qty", 0);
        frm.set_value("custom_secondary_uom_qty", 0);
        return;
    }

    // Step 1: Fetch primary qty from backend
    frappe.call({
        method: "sheetal_supply_chain.py.work_order.get_primary_uom_qty",
        args: {
            item_code: frm.doc.production_item,
            wo_qty: frm.doc.qty
        },
        callback: function (r_primary) {
            let primary_qty = r_primary.message || 0;
            
            // Step 2: Fetch secondary qty
            frappe.call({
                method: "sheetal_supply_chain.py.work_order.get_secondary_uom_qty",
                args: {
                    item_code: frm.doc.production_item,
                    primary_qty: primary_qty
                },
                callback: function (r_secondary) {
                    if (r_secondary.message !== undefined) {
                        frm.set_value(
                            "custom_secondary_uom_qty",
                            r_secondary.message
                        );
                        frm.set_value("custom_primary_uom_qty", primary_qty);
                    }
                }
            });
        }
    });
}

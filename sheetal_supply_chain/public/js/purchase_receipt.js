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

    // refresh(frm) {
    //     // Auto fetch when QI is auto-linked after submission
    //     frm.doc.items.forEach(item => {
    //         if (
    //             item.quality_inspection && 
    //             (!item.custom_fat || !item.custom_snf)
    //         ) {
    //             fetch_fat_snf(frm, item.doctype, item.name);
    //         }
    //     });
    // },

// refresh(frm) {
//     // Check server-side QI after cancel/amend
//     frappe.call({
//         method: "frappe.client.get",
//         args: {
//             doctype: frm.doc.doctype,
//             name: frm.doc.name
//         },
//         callback(r) {
//             if (!r.message) return;
//             let server_items = r.message.items;

//             server_items.forEach(s_item => {
//                 let l_item = frm.doc.items.find(i => i.name === s_item.name);
//                 if (!l_item) return;

//                 // QI changed in DB but not on form
//                 if (s_item.quality_inspection !== l_item.quality_inspection) {

//                     // 1️⃣ Update QI in database (no dirty state)
//                     frappe.db.set_value(
//                         "Purchase Receipt Item",
//                         l_item.name,
//                         "quality_inspection",
//                         s_item.quality_inspection
//                     );

//                     // 2️⃣ Update UI value → triggers your field event
//                     frappe.model.set_value(
//                         "Purchase Receipt Item",
//                         l_item.name,
//                         "quality_inspection",
//                         s_item.quality_inspection
//                     );
//                 }
//             });
//         }
//     });
// },


refresh(frm) {
    // Update all items with QI on form load
    frm.doc.items.forEach(item => {
        if (item.quality_inspection) {
            fetch_fat_snf(frm, item.doctype, item.name);
        }
    });
},
// NEW: Also refresh when returning to form
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
    // quality_inspection(frm, cdt, cdn) {
    //     fetch_fat_snf(frm, cdt, cdn);
    // }

    quality_inspection(frm, cdt, cdn) {
        fetch_fat_snf(frm, cdt, cdn);
    },
    // IMPORTANT: Also trigger on form render (when QI is auto-linked)
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
 

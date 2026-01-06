frappe.ui.form.on('Item', {
    validate(frm) {
        validate_unique_uoms(frm);
    },

    refresh(frm) {
        update_uom_checkbox_states(frm);
    }
});



frappe.ui.form.on('UOM Conversion Detail', {
    custom_is_primary_uom(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.custom_is_primary_uom) {
            row.custom_is_secondary_uom = 0;
            frappe.model.set_value(cdt, cdn, 'custom_is_secondary_uom', 0);
        }

        update_uom_checkbox_states(frm);
        validate_unique_uoms(frm);
    },

    custom_is_secondary_uom(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.custom_is_secondary_uom) {
            row.custom_is_primary_uom = 0;
            frappe.model.set_value(cdt, cdn, 'custom_is_primary_uom', 0);
        }

        update_uom_checkbox_states(frm);
        validate_unique_uoms(frm);
    }
});


function update_uom_checkbox_states(frm) {
    let grid = frm.fields_dict.uoms.grid;

    grid.update_docfield_property(
        'custom_is_secondary_uom',
        'read_only',
        function (doc) {
            return doc.custom_is_primary_uom === 1;
        }
    );

    grid.update_docfield_property(
        'custom_is_primary_uom',
        'read_only',
        function (doc) {
            return doc.custom_is_secondary_uom === 1;
        }
    );

    frm.refresh_field('uoms');
}


function validate_unique_uoms(frm) {
    let primary_count = 0;
    let secondary_count = 0;

    (frm.doc.uoms || []).forEach(row => {
        if (row.custom_is_primary_uom) primary_count++;
        if (row.custom_is_secondary_uom) secondary_count++;
    });

    if (primary_count > 1) {
        frappe.throw(__('Only one Primary UOM is allowed in UOM Conversion table.'));
    }

    if (secondary_count > 1) {
        frappe.throw(__('Only one Secondary UOM is allowed in UOM Conversion table.'));
    }
}

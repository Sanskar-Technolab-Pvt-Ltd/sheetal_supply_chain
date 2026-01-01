    frappe.ui.form.on("BOM", {

        refresh(frm) {

            // !? For UOM filter 
            setup_uom_filter(frm);
        },

        before_items_remove: function(frm) {
            setup_uom_filter(frm);
        },
        onload(frm) {

            // !? For UOM filter 
            setup_uom_filter(frm);

        },
    });

    frappe.ui.form.on("BOM Item", {

        uom(frm, cdt, cdn) {
        
            let row = locals[cdt][cdn];
            
            // Validate after user selects UOM
            if (row.item_code && row.uom) {
                validate_uom_selection(frm, cdt, cdn);
            }
        },
    });




    // ! Get Items UOM calling Function
    function setup_uom_filter(frm) {
        frm.fields_dict['items'].grid.get_field('uom').get_query = function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            
            if (!row || !row.item_code) {
                return {
                    filters: [
                        ['UOM', 'name', '=', '']
                    ]
                };
            }
            
            // Use custom whitelisted server method
            return {
                query: 'sheetal_supply_chain.py.bom.get_allowed_uoms_for_item',
                filters: {
                    item_code: row.item_code
                }
            };
        };
    }

    // ! Validate Those UOMS and sets in filter
    function validate_uom_selection(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (!row.item_code || !row.uom) return;
        
        // Check if UOM is valid for this item
        frappe.call({
            method: 'sheetal_supply_chain.py.bom.validate_item_uom',
            args: {
                item_code: row.item_code,
                uom: row.uom
            },
            callback: function(r) {
                if (r.message && !r.message.valid) {
                    frappe.msgprint({
                        title: __('Invalid UOM'),
                        indicator: 'red',
                        message: r.message.message || __('This UOM is not allowed for the selected item.')
                    });
                    
                    // Clear invalid UOM
                    setTimeout(() => {
                        frappe.model.set_value(cdt, cdn, 'uom', '');
                    }, 500);
                }
            }
        });
    }
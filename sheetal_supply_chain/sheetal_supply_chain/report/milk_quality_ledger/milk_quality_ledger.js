// milk_quality_ledger.js
// Client-side filters & formatter for "Milk Quality Ledger" report
// Enhanced with validation, error handling, and better UX

frappe.query_reports["Milk Quality Ledger"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
			on_change() {
				// Clear dependent filters when company changes
				frappe.query_report.set_filter_value("warehouse", []);
			}
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
			on_change() {
				// Validate date range
				const from_date = frappe.query_report.get_filter_value("from_date");
				const to_date = frappe.query_report.get_filter_value("to_date");
				
				if (from_date && to_date && from_date > to_date) {
					frappe.msgprint({
						title: __("Invalid Date Range"),
						message: __("From Date cannot be greater than To Date"),
						indicator: "red"
					});
					frappe.query_report.set_filter_value("from_date", to_date);
				}
			}
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			on_change() {
				// Validate date range
				const from_date = frappe.query_report.get_filter_value("from_date");
				const to_date = frappe.query_report.get_filter_value("to_date");
				
				if (from_date && to_date && from_date > to_date) {
					frappe.msgprint({
						title: __("Invalid Date Range"),
						message: __("To Date cannot be less than From Date"),
						indicator: "red"
					});
					frappe.query_report.set_filter_value("to_date", from_date);
				}
			}
		},
		{
			fieldname: "item_code",
			label: __("Items"),
			fieldtype: "MultiSelectList",
			get_data(txt) {
				return frappe.call({
					method: "frappe.desk.search.search_link",
					args: {
						doctype: "Item",
						txt: txt || "",
						page_length: 50,
						filters: {
							disabled: 0
						}
					}
				}).then(r => {
					if (r && r.message) {
						return r.message.map(d => ({
							value: d.value,
							description: d.description || ""
						}));
					}
					return [];
				}).catch(err => {
					console.error("Error fetching items:", err);
					return [];
				});
			}
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
			on_change() {
				// Optional: Auto-refresh if item group changes
				const item_group = frappe.query_report.get_filter_value("item_group");
				if (item_group) {
					frappe.query_report.refresh();
				}
			}
		},
		{
			fieldname: "brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "Brand",
			on_change() {
				const brand = frappe.query_report.get_filter_value("brand");
				if (brand) {
					frappe.query_report.refresh();
				}
			}
		},
		{
			fieldname: "warehouse",
			label: __("Warehouses"),
			fieldtype: "MultiSelectList",
			get_data(txt) {
				const company = frappe.query_report.get_filter_value("company");
				
				return frappe.db.get_link_options("Warehouse", txt, {
					company: company || "",
					disabled: 0
				}).then(options => {
					return options || [];
				}).catch(err => {
					console.error("Error fetching warehouses:", err);
					return [];
				});
			}
		},
		{
			fieldname: "voucher_type",
			label: __("Voucher Type"),
			fieldtype: "Link",
			options: "DocType",
			get_query() {
				return {
					filters: {
						istable: 0,
						issingle: 0
					}
				};
			}
		},
		{
			fieldname: "voucher_no",
			label: __("Voucher No"),
			fieldtype: "Data",
			description: __("Enter partial or full voucher number")
		},
		{
			fieldname: "batch_no",
			label: __("Batch No"),
			fieldtype: "Link",
			options: "Batch",
			get_query() {
				const item_code = frappe.query_report.get_filter_value("item_code");
				
				let filters = { disabled: 0 };
				
				if (item_code && item_code.length > 0) {
					filters.item = ["in", item_code];
				}
				
				return { filters: filters };
			}
		},
		
	],

	// onload(report) {
	// 	// Add custom buttons or actions
	// 	report.page.add_inner_button(__("Export"), function() {
	// 		frappe.query_report.export_report();
	// 	});
		
	// 	// Add refresh button with confirmation for large date ranges
	// 	const original_refresh = report.refresh;
	// 	report.refresh = function() {
	// 		const from_date = frappe.query_report.get_filter_value("from_date");
	// 		const to_date = frappe.query_report.get_filter_value("to_date");
			
	// 		if (from_date && to_date) {
	// 			const date_diff = frappe.datetime.get_day_diff(to_date, from_date);
				
	// 			if (date_diff > 365) {
	// 				frappe.confirm(
	// 					__("You are requesting data for more than 1 year. This may take some time. Continue?"),
	// 					() => original_refresh.call(report),
	// 					() => {}
	// 				);
	// 				return;
	// 			}
	// 		}
			
	// 		original_refresh.call(report);
	// 	};
	// },

	formatter(value, row, column, data, default_formatter) {
		// Apply custom formatting
		value = default_formatter(value, row, column, data);
		
		// Make voucher numbers clickable
		if (column.fieldname === "voucher_no" && data && data.voucher_type) {
			const voucher_type = data.voucher_type;
			const voucher_no = data.voucher_no;
			
			if (voucher_no && voucher_type) {
				value = `<a href="/app/${frappe.router.slug(voucher_type)}/${voucher_no}" target="_blank">${voucher_no}</a>`;
			}
		}
		
		return value;
	},

	// get_datatable_options(options) {
	// 	// Customize datatable appearance and behavior
	// 	return Object.assign(options, {
	// 		checkboxColumn: true,
	// 		events: {
	// 			onCheckRow(row) {
	// 				// Handle row selection
	// 				console.log("Row selected:", row);
	// 			}
	// 		}
	// 	});
	// }
};
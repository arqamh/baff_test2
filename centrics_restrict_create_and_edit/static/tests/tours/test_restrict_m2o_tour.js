/** @odoo-module **/

/**
 * Tour: verify that the Many2one restriction hides "Create" / "Create and
 * Edit" options and the "New" button in Search More dialog.
 *
 * Prerequisites (set up by the Python HttpCase):
 *   - A restriction config for sale.order / partner_id is enabled.
 *   - A customer "Restrict Test Partner" exists.
 *
 * NOTE: Odoo 16 uses hash-based routing (/web#action=...) and the "text"
 * run helper for typing into inputs.
 */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_restrict_m2o_create_hidden", {
    url: "/web#action=sale.action_quotations_with_onboarding",
    steps: () => [
        // ---- Step 1: Create a new Sale Order ----
        {
            content: "Create new sales order",
            trigger: ".o_list_button_add",
            run: "click",
        },
        // ---- Step 2: Type a non-existent name in the Customer field ----
        {
            content: "Type non-existent customer name in partner_id",
            trigger: ".o_field_widget[name=partner_id] input",
            run: "text ZZZ_NoSuchCustomer_999",
        },
        // ---- Step 3: Wait for dropdown, verify NO Create option exists ----
        {
            content: "Verify no 'Create' option in dropdown",
            trigger:
                ".o-autocomplete--dropdown-menu:not(:has(.o_m2o_dropdown_option_create)):not(:has(.o_m2o_dropdown_option_create_edit))",
        },
        // ---- Step 4: Click Search More to open the dialog ----
        {
            content: "Click 'Search More...' to open selection dialog",
            trigger: ".o_m2o_dropdown_option_search_more",
            run: "click",
        },
        // ---- Step 5: Verify the dialog has NO 'New' button ----
        {
            content: "Verify dialog has no 'New' button (noCreate=true)",
            trigger: ".o_select_create_dialog_content",
        },
        {
            content: "Confirm no 'New' button in the dialog footer",
            trigger: ".modal-footer:not(:has(.o_create_button))",
        },
        // ---- Step 6: Close the dialog ----
        {
            content: "Close the dialog",
            trigger: ".modal-footer .o_form_button_cancel",
            run: "click",
        },
        // ---- Step 7: Now select an existing customer (selection still works) ----
        {
            content: "Clear and type existing customer name",
            trigger: ".o_field_widget[name=partner_id] input",
            run: "text Restrict Test Partner",
        },
        {
            content: "Select existing customer from dropdown",
            trigger:
                ".o-autocomplete--dropdown-item:contains('Restrict Test Partner')",
            run: "click",
        },
        // ---- Step 8: Verify customer was set ----
        {
            content: "Verify customer field is set",
            trigger: ".o_field_widget[name=partner_id] .o_form_uri",
        },
    ],
});

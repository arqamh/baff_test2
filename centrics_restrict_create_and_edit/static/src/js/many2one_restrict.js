/** @odoo-module **/

/**
 * Restrict Create and Edit on Many2one fields.
 *
 * The backend's `ir.http.session_info` override injects:
 *     session.restrict_create_and_edit = {
 *         "purchase.order.line": ["product_id", "product_uom"],
 *         ...
 *     }
 *
 * We patch Many2OneField.Many2XAutocompleteProps so that when a field is
 * restricted we:
 *   1. Set quickCreate: null and activeActions.create/createEdit: false
 *      (standard Odoo path that drives the native dropdown options)
 *   2. Set nodeOptions.no_create / no_create_edit: true
 *      (web_m2x_options path — its loadOptionsSource guards on these flags)
 *
 * NOTE: Odoo 16 uses patch(obj, name, extension) — 3-argument form.
 */

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

function isFieldRestricted(resModel, fieldName) {
    const map = session.restrict_create_and_edit;
    if (!map || !resModel || !fieldName) {
        return false;
    }
    const fields = map[resModel];
    return Array.isArray(fields) && fields.includes(fieldName);
}

patch(Many2OneField.prototype, "centrics_restrict_create_and_edit", {
    get Many2XAutocompleteProps() {
        const props = this._super();
        const resModel = this.props.record && this.props.record.resModel;
        if (!isFieldRestricted(resModel, this.props.name)) {
            return props;
        }
        return {
            ...props,
            // Standard Odoo path: quickCreate=null prevents the "Create" option;
            // activeActions flags prevent the "Create and edit..." option.
            quickCreate: null,
            activeActions: {
                ...(props.activeActions || {}),
                create: false,
                createEdit: false,
            },
            // web_m2x_options path: loadOptionsSource checks these nodeOptions
            // flags before adding "Create" and "Create and edit..." to the list.
            nodeOptions: {
                ...(props.nodeOptions || {}),
                no_create: true,
                no_create_edit: true,
            },
        };
    },
});
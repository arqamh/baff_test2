/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WorkingEmployeePopup } from '@mrp_workorder_hr/components/working_employee_popup';

patch(WorkingEmployeePopup.prototype,"baff_manufacturing_modifications.WorkingEmployeePopup", {
    // Override the Employee Change view and added a method for cancelation button
     setup() {
        this._super();
     },

    cancel() {
        this.props.onClosePopup('WorkingEmployeePopup', true);
    }
});
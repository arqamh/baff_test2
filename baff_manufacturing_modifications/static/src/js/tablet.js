/** @odoo-module **/

import Tablet from '@mrp_workorder/components/tablet';
import { patch } from 'web.utils';

patch(Tablet.prototype, 'baff_manufacturing_modifications.tablet', {
    // override tablet view and add job title for the employee details
    setup() {
        this._super();
    },

    popupAddEmployee() {
        const list = this.data.employee_list.filter(e => ! this.data.employee_ids.includes(e.id)).map((employee) => {
            return {
                id: employee.id,
                item: employee,
                label: employee.name,
                isSelected: false,
                job_title: employee.job_title
            };
        });
        const title = this.env._t('Change Worker');
        this.showPopup({ title, list }, 'SelectionPopup');
    },
});
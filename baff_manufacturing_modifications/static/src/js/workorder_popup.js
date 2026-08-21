/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { SelectionPopup } from "@mrp_workorder_hr/components/popup";

patch(SelectionPopup.prototype,"baff_manufacturing_modifications.SelectionPopupPatch", {
    // Override Employee selection view and added a filteration and search option
     setup() {
        this.state = useState({
            filteredList: this.props.popupData.list,
            searchKeyword: "",
        });

     },

    onKeyUp(event) {
        const value = event.target.value.toLowerCase();
        this.state.searchKeyword = value;
        // this.state.filteredList = this.props.popupData.list.filter(emp =>
        //     emp.label.toLowerCase().includes(value));
        this.state.filteredList = this.props.popupData.list.filter(emp =>
            (emp.label && emp.label.toLowerCase().includes(value)) ||
            (emp.job_title && emp.job_title.toLowerCase().includes(value))
        );
    },
});
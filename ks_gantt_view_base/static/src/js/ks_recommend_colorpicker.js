/* @odoo-module */

import { registry } from "@web/core/registry";
const { Component,useState,onWillUpdateProps } = owl;

export class ks_gantt_color_picker extends Component {
    setup() {
        this.state = useState({
            ks_gantt_color_picker: this.props.value});

        onWillUpdateProps((nextProps) => {
            this.state.ks_gantt_color_picker = nextProps.value;
        });
    }
        _ClickColor(ev)
       {
       ev.target.value;
        this.props.update(ev.target.value);

               }
};
ks_gantt_color_picker.template = 'ks_gantt_color_picker';
registry.category("fields").add("ks_gantt_color_picker", ks_gantt_color_picker);

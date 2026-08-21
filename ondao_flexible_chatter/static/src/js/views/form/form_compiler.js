/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import {FormCompiler} from "@web/views/form/form_compiler";
import { MailFormCompiler } from "@mail/views/form/form_compiler";
import { append, createElement, setAttributes } from "@web/core/utils/xml";

patch(MailFormCompiler.prototype, "flexible_chatter", {
    compile() {
        const res = this._super.apply(this, arguments);
        const chatterContainerHookXml = res.querySelector(".o_FormRenderer_chatterContainer");
        if (!chatterContainerHookXml) {
            return res;
        }

        if (odoo.web_chatter_position === "manual") {
            setAttributes(chatterContainerHookXml, {
                "t-att-class": "{'less': chatterPreviewState.chatterLess,'hidden': chatterPreviewState.chatterHidden,'hide_chatter_control': true}",
                "t-ref": "chatterContainer",
            });

            const chatterContainerControlHookXml = createElement("div");
            chatterContainerControlHookXml.classList.add("o_chatter_control");
            setAttributes(chatterContainerControlHookXml, {
                "t-on-click": "togglePreview",
            });
            append(chatterContainerHookXml, chatterContainerControlHookXml);

            const chatterContainerResizeHookXml = createElement("span");
            chatterContainerResizeHookXml.classList.add("o_resize");
            setAttributes(chatterContainerResizeHookXml, {
                "t-on-click.stop.prevent": "",
                "t-on-mousedown.stop.prevent": "onStartResize",
            });
            append(chatterContainerHookXml, chatterContainerResizeHookXml);
        } else if (odoo.web_chatter_position === "bottom") {
            setAttributes(chatterContainerHookXml, {
                "t-if": false,
            });
        }

        return res;
    },
});

patch(FormCompiler.prototype, 'flexible_chatter', {
    compile(node, params) {
        const res = this._super(node, params);

        const chatterContainerHookXml = res.querySelector(
            ".o_FormRenderer_chatterContainer:not(.o-isInFormSheetBg)"
        );
        if (!chatterContainerHookXml) {
            return res;
        }
        if (chatterContainerHookXml.parentNode.classList.contains("o_form_sheet")) {
            return res;
        }

        if (odoo.web_chatter_position === "manual") {
            return res;
        } else if (odoo.web_chatter_position === "bottom") {
            if (params.hasAttachmentViewerInArch) {
                const sheetBgChatterContainerHookXml = res.querySelector(".o_FormRenderer_chatterContainer.o-isInFormSheetBg");
                sheetBgChatterContainerHookXml.setAttribute("t-if", true);
                chatterContainerHookXml.setAttribute("t-if", false);
            } else {
                const formSheetBgXml = res.querySelector(".o_form_sheet_bg");
                if (!formSheetBgXml) {
                    return res;
                }
                const sheetBgChatterContainerHookXml = chatterContainerHookXml.cloneNode(true);
                sheetBgChatterContainerHookXml.classList.add("o-isInFormSheetBg");
                sheetBgChatterContainerHookXml.setAttribute("t-if", true);
                append(formSheetBgXml, sheetBgChatterContainerHookXml);

                const sheetBgChatterContainerXml = sheetBgChatterContainerHookXml.querySelector("ChatterContainer");
                sheetBgChatterContainerXml.setAttribute("isInFormSheetBg", "true");

                chatterContainerHookXml.setAttribute("t-if", false);
            }
        }

        return res;
    },
});


/** @odoo-module */

const { useState, useRef } = owl;
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, "web_chatter_position", {
    setup() {
        this._super.apply();
        this.chatterPreviewState = useState({
            chatterHidden: false,
            currentWidth: 0
        });
        this.chatterContainer = useRef("chatterContainer");
    },

    onStartResize(ev) {
        if (ev.button !== 0) {
            return;
        }

        const initialX = ev.pageX;
        const initialWidth = this.chatterContainer.el.offsetWidth;
        const resizeStoppingEvents = ["keydown", "mousedown", "mouseup"];

        this.chatterContainer.el.classList.remove("less");

        const resizePanel = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            const delta = ev.pageX - initialX;
            const newWidth = Math.max(10, initialWidth - delta);
            this.chatterContainer.el.style["max-width"] = `${newWidth}px`;

        };
        document.addEventListener("mousemove", resizePanel, true);

        const stopResize = (ev) => {
            if (ev.type === "mousedown" && ev.button === 0) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            document.removeEventListener("mousemove", resizePanel, true);
            resizeStoppingEvents.forEach((stoppingEvent) => {
                document.removeEventListener(stoppingEvent, stopResize, true);
            });

            document.activeElement.blur();
        };

        resizeStoppingEvents.forEach((stoppingEvent) => {
            document.addEventListener(stoppingEvent, stopResize, true);
        });
    },

    togglePreview(ev) {
        this.chatterPreviewState.chatterHidden = !this.chatterPreviewState.chatterHidden ;
        if (this.chatterPreviewState.chatterHidden === true) {
            this.chatterPreviewState.currentWidth = this.chatterContainer.el.style["max-width"];
            this.chatterContainer.el.classList.remove("hide_chatter_control");
            this.chatterContainer.el.classList.add("show_chatter_control");
            this.chatterContainer.el.style["max-width"] = "";
        } else {
            this.chatterContainer.el.style["max-width"] = this.chatterPreviewState.currentWidth;
            this.chatterContainer.el.classList.remove("show_chatter_control");
            this.chatterContainer.el.classList.add("hide_chatter_control");
        }
    },

});


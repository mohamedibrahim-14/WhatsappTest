/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { StateSelectionField } from "@web/views/fields/state_selection/state_selection_field";

// Patch the StateSelectionField (used in form/list views with widget="state_selection")
patch(StateSelectionField.prototype, {
    setup() {
        super.setup(...arguments);
        // Add black color for our custom done_closed state
        this.colors["done_closed"] = "black";
    },
});


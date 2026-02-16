# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WhatsAppTemplateButton(models.Model):
    _inherit = 'whatsapp.template.button'

    trigger_sale_order_confirm = fields.Boolean(
        string='Confirm Order on Tap',
        default=False,
        help='When the customer taps this Quick Reply button, the linked website sale order '
             'will be confirmed (action_confirm). Only use with Quick Reply buttons on '
             'order confirmation templates.'
    )
    
    trigger_sale_order_cancel = fields.Boolean(
        string='Cancel Order on Tap',
        default=False,
        help='When the customer taps this Quick Reply button, the linked website sale order '
             'will be cancelled (action_cancel). Only use with Quick Reply buttons on '
             'order confirmation templates.'
    )

    @api.constrains('trigger_sale_order_confirm', 'trigger_sale_order_cancel', 'button_type')
    def _check_trigger_actions_quick_reply(self):
        for btn in self:
            if btn.button_type != 'quick_reply':
                if btn.trigger_sale_order_confirm:
                    from odoo.exceptions import ValidationError
                    from odoo import _
                    raise ValidationError(
                        _('"Confirm Order on Tap" is only supported for Quick Reply buttons.')
                    )
                if btn.trigger_sale_order_cancel:
                    from odoo.exceptions import ValidationError
                    from odoo import _
                    raise ValidationError(
                        _('"Cancel Order on Tap" is only supported for Quick Reply buttons.')
                    )
            
            # Prevent both triggers on same button
            if btn.trigger_sale_order_confirm and btn.trigger_sale_order_cancel:
                from odoo.exceptions import ValidationError
                from odoo import _
                raise ValidationError(
                    _('A button cannot have both "Confirm Order" and "Cancel Order" triggers enabled.')
                )
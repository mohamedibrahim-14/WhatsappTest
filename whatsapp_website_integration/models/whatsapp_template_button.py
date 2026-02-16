# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WhatsAppTemplateButton(models.Model):
    _inherit = 'whatsapp.template.button'

    trigger_sale_order_confirm = fields.Boolean(
        string='Confirm Order on Tap',
        default=False,
        help='When the customer taps this Quick Reply button, the linked website sale order '
             'will be confirmed (action_confirm). Only use with Quick Reply buttons on '
             'order confirmation templates.'
    )

    @api.constrains('trigger_sale_order_confirm', 'button_type')
    def _check_trigger_sale_order_confirm_quick_reply(self):
        for btn in self:
            if btn.trigger_sale_order_confirm and btn.button_type != 'quick_reply':
                from odoo.exceptions import ValidationError
                from odoo import _
                raise ValidationError(
                    _('"Confirm Order on Tap" is only supported for Quick Reply buttons.')
                )

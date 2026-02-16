# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def message_post(self, *, message_type='notification', **kwargs):
        new_msg = super().message_post(message_type=message_type, **kwargs)

        if (
            self.channel_type != 'whatsapp'
            or message_type != 'whatsapp_message'
            or not new_msg.body
        ):
            return new_msg

        # Only handle inbound messages (customer tapped a button)
        if new_msg.author_id != self.whatsapp_partner_id:
            return new_msg

        button_text = (html2plaintext(new_msg.body) or '').strip()
        if not button_text:
            return new_msg

        # Check if this button text is configured to confirm a sale order
        confirm_button = self.env['whatsapp.template.button'].sudo().search([
            ('trigger_sale_order_confirm', '=', True),
            ('name', '=', button_text),
        ], limit=1)
        if not confirm_button:
            return new_msg

        # Channel must be linked to a document (the message we sent from)
        related_msg = self.whatsapp_mail_message_id
        if not related_msg or related_msg.model != 'sale.order':
            _logger.debug(
                "WhatsApp button tap '%s' not applied: channel not linked to sale.order",
                button_text
            )
            return new_msg

        order = self.env['sale.order'].sudo().browse(related_msg.res_id)
        if not order.exists():
            return new_msg

        if order.state not in ('draft', 'sent'):
            _logger.info(
                "WhatsApp confirm button tap for order %s ignored: state is %s",
                order.name, order.state
            )
            return new_msg

        try:
            order.action_confirm()
            _logger.info(
                "Sale order %s confirmed via WhatsApp button tap '%s'",
                order.name, button_text
            )
        except Exception as e:
            _logger.exception(
                "Failed to confirm order %s from WhatsApp button tap: %s",
                order.name, e
            )

        return new_msg

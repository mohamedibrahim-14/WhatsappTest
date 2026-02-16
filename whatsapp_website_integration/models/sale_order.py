# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    whatsapp_msg_sent = fields.Boolean(
        string='WhatsApp Confirmation Sent',
        default=False,
        readonly=True,
        help='Indicates if WhatsApp confirmation message has been sent'
    )

    def _find_value_from_field_path(self, field_path):
        if field_path == 'amount':
            return f"{self.amount_total} {self.currency_id.name}"
        if field_path == 'link':
            return self.get_portal_url()  # or a custom payment URL
        if field_path == 'order_summary':
            lines = []
            for line in self.order_line:
                lines.append(f"- {line.product_id.display_name}: {line.product_uom_qty} x {line.price_unit} {self.currency_id.name}")
            return "\n".join(lines)
        return super()._find_value_from_field_path(field_path)

    # ---------------------------------------------------------
    # CORE WHATSAPP SEND LOGIC
    # ---------------------------------------------------------

    def _send_order_confirmation_whatsapp(self):
        """Send WhatsApp confirmation message for the order"""
        self.ensure_one()
        _logger.info("Starting WhatsApp send for order %s", self.name)

        template = self.env['whatsapp.template'].get_order_confirmation_template()
        if not template:
            _logger.warning(
                "No WhatsApp template configured for auto-send (order %s)",
                self.name
            )
            return False

        phone = self.partner_id.mobile or self.partner_id.phone
        if not phone:
            _logger.warning(
                "Customer %s has no phone number (order %s)",
                self.partner_id.name, self.name
            )
            return False

        if 'whatsapp.composer' not in self.env:
            _logger.error("Odoo WhatsApp module is not installed")
            return False

        return self._send_via_standard_whatsapp(template, phone)

    def _send_via_standard_whatsapp(self, template, phone):
        """Send message using standard Odoo WhatsApp"""
        _logger.info(
            "Preparing standard WhatsApp composer for order %s (phone: %s)",
            self.name, phone
        )

        try:
            composer = self.env['whatsapp.composer'].with_context(
                active_model='sale.order',
                active_id=self.id,
                active_ids=[self.id],
            ).sudo().create({
                'res_model': 'sale.order',
                'wa_template_id': template.id,
                'phone': phone,
            })

            _logger.info(
                "WhatsApp composer created (ID: %s) for order %s",
                composer.id, self.name
            )

            try:
                composer.action_send_whatsapp_template()
            except UserError as ue:
                _logger.error(
                    "WhatsApp template rendering error for order %s: %s",
                    self.name, ue
                )
                return False

            self.whatsapp_msg_sent = True
            _logger.info(
                "WhatsApp confirmation successfully sent for order %s",
                self.name
            )
            return True

        except Exception as e:
            _logger.error(
                "Standard WhatsApp send failed for order %s: %s",
                self.name, str(e)
            )
            import traceback
            _logger.error(traceback.format_exc())
            return False

    # ---------------------------------------------------------
    # MANUAL ACTION
    # ---------------------------------------------------------

    def action_send_whatsapp_manual(self):
        """Manual action to send WhatsApp confirmation"""
        self.ensure_one()
        _logger.info("Manual WhatsApp send triggered for order %s", self.name)

        template = self.env['whatsapp.template'].get_order_confirmation_template()
        if not template:
            _logger.warning(
                "Manual send blocked: no template configured (order %s)",
                self.name
            )
            raise UserError(_(
                'No WhatsApp template is configured for auto-send.'
            ))

        phone = self.partner_id.mobile or self.partner_id.phone
        if not phone:
            _logger.warning(
                "Manual send blocked: customer %s has no phone (order %s)",
                self.partner_id.name, self.name
            )
            raise UserError(_(
                'Customer %s has no phone number.'
            ) % self.partner_id.name)

        result = self._send_order_confirmation_whatsapp()

        if result:
            _logger.info(
                "Manual WhatsApp send succeeded for order %s",
                self.name
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp Sent'),
                    'message': _('WhatsApp confirmation message sent successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

        _logger.error(
            "Manual WhatsApp send failed for order %s",
            self.name
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Error'),
                'message': _('Failed to send WhatsApp message. Check the logs for details.'),
                'type': 'danger',
                'sticky': False,
            }
        }

    # ---------------------------------------------------------
    # OVERRIDES
    # ---------------------------------------------------------

    def action_quotation_sent(self):
        """Override to send WhatsApp message on order confirmation"""
        _logger.info("Confirming sale order(s): %s", self.ids)
        res = super().action_quotation_send()

        for order in self:
            if order.website_id and not order.whatsapp_msg_sent:
                _logger.info(
                    "Auto-sending WhatsApp for website order %s",
                    order.name
                )
                order._send_order_confirmation_whatsapp()

        return res

    def _cart_update_order_line(self, product_id, quantity, order_line_id, **kwargs):
        """Override to handle website cart updates"""
        _logger.debug(
            "Cart update on order %s (product_id=%s, qty=%s)",
            self.id, product_id, quantity
        )
        return super()._cart_update_order_line(
            product_id, quantity, order_line_id, **kwargs
        )

    def _create_payment_transaction(self, vals):
        """Override to hook into payment creation"""
        _logger.info(
            "Creating payment transaction for order %s",
            self.name
        )
        transaction = super()._create_payment_transaction(vals)
        _logger.info(
            "Payment transaction %s created for order %s",
            transaction.id if transaction else None,
            self.name
        )
        return transaction

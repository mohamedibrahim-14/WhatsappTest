# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _set_done(self):
        res = super()._set_done()

        for tx in self:
            _logger.info(
                "Transaction %s done (provider: %s)",
                tx.reference, tx.provider_code
            )

            # ONLY Pay on Site
            if tx.provider_code != 'manual':
                continue

            for order in tx.sale_order_ids:
                _logger.info("Evaluating order %s for WhatsApp", order.name)

                if not order.website_id:
                    continue
                if order.state != 'sent':
                    continue
                if order.invoice_status != 'no':
                    continue
                if order.whatsapp_msg_sent:
                    continue

                _logger.info(
                    "Sending Pay-on-Site WhatsApp reminder for order %s",
                    order.name
                )

                order._send_order_confirmation_whatsapp()

        return res

import hashlib
import logging

from odoo import models

_logger = logging.getLogger(__name__)


def _hash_norm(value):
    """Normalize and SHA256-hash a string for Meta user_data."""
    if not value:
        return False
    v = str(value).strip().lower()
    if not v:
        return False
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _meta_capi_send_purchase_event(self):
        """Send a Purchase event to Meta CAPI for website orders."""
        meta_api = self.env["meta.conversions.api"]

        for order in self:
            # Only website orders, skip backend-only orders if you want stricter filter
            if not order.website_id:
                continue

            # Build user_data from partner info (email / phone)
            user_data = {
                "em": _hash_norm(order.partner_id.email),
                "ph": _hash_norm(order.partner_id.mobile or order.partner_id.phone),
            }
            # Remove empty values
            user_data = {k: v for k, v in user_data.items() if v}
            if not user_data:
                _logger.info(
                    "Meta CAPI: skipping order %s because no usable customer identifiers were found.",
                    order.id,
                )
                continue

            custom_data = {
                "currency": order.currency_id.name,
                "value": float(order.amount_total),
                "content_ids": [line.product_id.id for line in order.order_line],
                "content_type": "product",
            }

            meta_api.send_event(
                event_name="Purchase",
                user_data=user_data,
                custom_data=custom_data,
            )

    def action_confirm(self):
        """On order confirmation, also send a Purchase event to Meta CAPI."""
        res = super().action_confirm()
        try:
            self._meta_capi_send_purchase_event()
        except Exception:
            _logger.exception(
                "Meta CAPI: error while sending Purchase event for orders %s", self.ids
            )
        return res


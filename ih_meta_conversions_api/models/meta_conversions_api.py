import logging
import time

import requests

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MetaConversionsApi(models.AbstractModel):
    """Helper model to send events to Meta (Facebook) Conversions API.

    Usage example (Python code, e.g. server action):

        self.env['meta.conversions.api'].send_event(
            event_name='Purchase',
            user_data={'client_user_agent': self.env.context.get('user_agent')},
            custom_data={
                'currency': 'USD',
                'value': order.amount_total,
            },
        )
    """

    _name = "meta.conversions.api"
    _description = "Meta Conversions API Helper"

    @api.model
    def _get_config(self):
        ICP = self.env["ir.config_parameter"].sudo()
        enabled = ICP.get_param("meta_capi.enabled") in (True, "True", "true", "1")
        pixel_id = ICP.get_param("meta_capi.pixel_id")
        access_token = ICP.get_param("meta_capi.access_token")
        test_event_code = ICP.get_param("meta_capi.test_event_code")
        return {
            "enabled": enabled,
            "pixel_id": pixel_id,
            "access_token": access_token,
            "test_event_code": test_event_code,
        }

    @api.model
    def send_event(
        self,
        event_name,
        event_time=None,
        event_id=None,
        user_data=None,
        custom_data=None,
        test_event_code=None,
        raise_on_error=False,
    ):
        """Send a single event to Meta Conversions API.

        :param event_name: e.g. 'PageView', 'Purchase', 'AddToCart'
        :param event_time: Unix timestamp (int). Defaults to now UTC.
        :param event_id: Optional unique ID for deduplication with Pixel events.
        :param user_data: Dict with user-related data (email, phone, client IP, UA, etc.).
                          Values should follow Meta's requirements (usually SHA256-hashed).
        :param custom_data: Dict with business data (value, currency, content_ids, etc.).
        :param test_event_code: Optional string from Events Manager (overrides config if set).
        :param raise_on_error: If True, raise UserError on HTTP errors; otherwise, log.
        """
        config = self._get_config()
        if not config["enabled"]:
            _logger.info("Meta Conversions API disabled in configuration; skipping event.")
            return False

        pixel_id = config["pixel_id"]
        access_token = config["access_token"]
        if not pixel_id or not access_token:
            msg = _(
                "Meta Conversions API is not fully configured. "
                "Please set Pixel ID and Access Token in Website settings."
            )
            if raise_on_error:
                raise UserError(msg)
            _logger.warning(msg)
            return False

        url = f"https://graph.facebook.com/v17.0/{pixel_id}/events"
        payload = {
            "data": [
                {
                    "event_name": event_name,
                    "event_time": int(event_time or time.time()),
                    "event_id": event_id,
                    "action_source": "website",
                    "user_data": user_data or {},
                    "custom_data": custom_data or {},
                }
            ]
        }

        # Remove empty keys that Meta may reject
        for event in payload["data"]:
            if not event["event_id"]:
                event.pop("event_id")

        params = {"access_token": access_token}

        # Prefer explicit call-time test_event_code, otherwise config
        tec = test_event_code or config.get("test_event_code")
        if tec:
            params["test_event_code"] = tec

        try:
            response = requests.post(url, json=payload, params=params, timeout=10)
            if not response.ok:
                _logger.error(
                    "Meta Conversions API error [%s]: %s",
                    response.status_code,
                    response.text,
                )
                if raise_on_error:
                    raise UserError(
                        _("Meta Conversions API error: %s") % response.text
                    )
                return False

            _logger.info("Meta Conversions API event sent successfully: %s", response.text)
            return True
        except Exception as e:  # pragma: no cover - network failures
            _logger.exception("Failed to send event to Meta Conversions API: %s", e)
            if raise_on_error:
                raise UserError(
                    _("Failed to send event to Meta Conversions API: %s") % e
                )
            return False


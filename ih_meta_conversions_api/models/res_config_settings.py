from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Meta Pixel (Client-side) Settings
    meta_pixel_enabled = fields.Boolean(
        string="Enable Meta Pixel",
        config_parameter="meta_capi.pixel_enabled",
        help="Enable client-side Meta Pixel tracking on your website.",
    )
    meta_pixel_id = fields.Char(
        string="Meta Pixel ID",
        config_parameter="meta_capi.pixel_id",
        help="Your Meta Pixel ID for client-side tracking.",
    )

    # Meta Conversions API (Server-side) Settings
    meta_capi_enabled = fields.Boolean(
        string="Enable Meta Conversions API",
        config_parameter="meta_capi.enabled",
        help="Enable server-side tracking of events to Meta (Facebook) via the Conversions API.",
    )
    meta_capi_access_token = fields.Char(
        string="Meta Conversions API Access Token",
        config_parameter="meta_capi.access_token",
        help="Generated from Meta Events Manager for this Pixel.",
    )
    meta_capi_test_event_code = fields.Char(
        string="Test Event Code",
        config_parameter="meta_capi.test_event_code",
        help="Optional test code from Events Manager, used while validating events.",
    )

    @api.model
    def get_values(self):
        """Ensure backward compatibility if config parameters are missing."""
        res = super().get_values()
        ICP = self.env["ir.config_parameter"].sudo()
        res.update(
            # Pixel settings
            meta_pixel_enabled=ICP.get_param("meta_capi.pixel_enabled", default=False),
            meta_pixel_id=ICP.get_param("meta_capi.pixel_id", default=""),
            # CAPI settings
            meta_capi_enabled=ICP.get_param("meta_capi.enabled", default=False),
            meta_capi_access_token=ICP.get_param("meta_capi.access_token", default=""),
            meta_capi_test_event_code=ICP.get_param("meta_capi.test_event_code", default=""),
        )
        return res


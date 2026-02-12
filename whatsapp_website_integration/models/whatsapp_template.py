# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WhatsAppTemplate(models.Model):
    _inherit = 'whatsapp.template'
    
    auto_send_on_order = fields.Boolean(
        string='Auto Send on Website Order',
        default=False,
        help='If checked, this template will be automatically sent when a customer places an order on the website'
    )
    
    @api.model
    def get_order_confirmation_template(self):
        """Get the template marked for auto-send on orders"""
        template = self.search([
            ('auto_send_on_order', '=', True),
            ('status', '=', 'approved')
        ], limit=1)
        return template

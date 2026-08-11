from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class CustomInventoryQuant(models.Model):
    _name = 'custom.inventory.quant'
    _description = 'Custom Inventory Quant'

    # product_id = fields.Many2one(
    #     'custom.inventory.product',
    #     string='Asset Product',
    #     domain="[('location_id', '=', False)]",
    #     required=True
    # )
    asset_type = fields.Many2one('assets.type', string='Asset Type', required=True)
    location_id = fields.Many2one('custom.inventory.location', string='Location', required=True)
    quantity = fields.Integer(string='Quantity')
    availability_no = fields.Integer(string="Available", tracking=True)
    un_availability_no = fields.Integer(string="Unavailable", tracking=True,readonly=1)
    lines_requests_id = fields.Many2one('requests.inventory')
    from_location = fields.Boolean(string="From Location",default=lambda self: self.env.context.get('from_location', False))



    @api.onchange('asset_type', 'quantity')
    def _onchange_asset_type_or_quantity(self):
        for rec in self:
            rec._compute_availability_values()

    @api.onchange('lines_requests_id')
    def _onchange_lines_requests_id(self):
        for rec in self:
            if rec.lines_requests_id and rec.lines_requests_id.location_id:
                rec.location_id = rec.lines_requests_id.location_id

    # --------- Shared method to compute availability ------------
    def _compute_availability_values(self):
        for rec in self:
            _logger.warning(
                f"[START Availability] Asset Type: {rec.asset_type.name if rec.asset_type else 'None'} | "
                f"ID: {rec.asset_type.id if rec.asset_type else 'N/A'} | Quantity: {rec.quantity}")

            if rec.asset_type and rec.quantity:
                products = self.env['custom.inventory.product'].search([
                    ('asset_name', '=', rec.asset_type.id),
                    ('asset_status', '=', 'transferable'),
                    ('location_id', '!=', False)
                ])

                available_count = len(products)
                rec.availability_no = min(rec.quantity, available_count)
                rec.un_availability_no = rec.quantity - rec.availability_no

                _logger.warning(
                    f"[RESULT] Found {available_count} related active assets with location. "
                    f"Available: {rec.availability_no}, Unavailable: {rec.un_availability_no}"
                )
            else:
                rec.availability_no = 0
                rec.un_availability_no = rec.quantity or 0
                _logger.warning("[SKIPPED] asset_type or quantity not set.")

    # --------- CREATE ---------
    @api.model
    def create(self, vals):
        # Auto-fill asset_type based on selected product
        if vals.get('product_id') and not vals.get('asset_type'):
            product = self.env['custom.inventory.product'].browse(vals['product_id'])
            if product.asset_name:
                vals['asset_type'] = product.asset_name.id

        # Autofill location before record creation
        if not vals.get('location_id') and vals.get('lines_requests_id'):
            request = self.env['requests.inventory'].browse(vals['lines_requests_id'])
            if request and request.location_id:
                vals['location_id'] = request.location_id.id

        record = super().create(vals)

        # Compute availability
        record._compute_availability_values()

        return record

    # --------- WRITE ---------
    def write(self, vals):
        for rec in self:
            if vals.get('product_id') and not vals.get('asset_type'):
                product = self.env['custom.inventory.product'].browse(vals['product_id'])
                if product.asset_name:
                    vals['asset_type'] = product.asset_name.id

        res = super().write(vals)

        # استخدم context flag عشان تمنع الـ recursion
        if not self.env.context.get('no_recompute_availability'):
            for rec in self:
                if not rec.location_id and rec.lines_requests_id and rec.lines_requests_id.location_id:
                    rec.location_id = rec.lines_requests_id.location_id

                rec.with_context(no_recompute_availability=True)._compute_availability_values()

        return res


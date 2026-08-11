from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CustomStockMove(models.Model):
    _name = 'custom.inventory.move'
    _description = 'Custom Inventory Move'

    product_id = fields.Many2one('custom.inventory.product', string='Asset',required=True)
    asset_type = fields.Many2one('assets.type', string="Asset Type")
    analytic_account_asset = fields.Many2one('account.analytic.account', string="Analytic Account")
    inventory_location_ids = fields.One2many(
        'custom.inventory.location',
        'analytic_account_asset',
        string='Inventory Operations'
    )
    location_id = fields.Many2one('custom.inventory.location', string='Source Location')
    location_dest_id = fields.Many2one('custom.inventory.location', string='Destination Location', required=True)
    picking_id = fields.Many2one('custom.inventory.picking', string='Picking')
    operation_id = fields.Many2one('custom.inventory.operation', string='Operation')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='State', default='draft')
    track_serial = fields.Char(related='product_id.track_serial', string='Serial Number')
    moved_by = fields.Many2one('res.users', string='Moved By', default=lambda self: self.env.user)
    move_date = fields.Datetime(string='Movement Date', default=fields.Datetime.now)

    available_asset_type_ids = fields.Many2many(
        'assets.type',
        compute='_compute_available_asset_types'
    )

    @api.depends('location_id')
    def _compute_available_asset_types(self):
        for rec in self:
            if rec.location_id:
                rec.available_asset_type_ids = rec.location_id.assigned_product_ids.mapped('asset_name')
            else:
                rec.available_asset_type_ids = False

    @api.onchange('product_id')
    def _onchange_product_id_set_locations(self):
        for rec in self:
             if rec.operation_id:
                 if not rec.location_id:
                     rec.location_id = rec.operation_id.default_source_location_id
                     _logger.warning("Auto-set Source Location from operation: %s", rec.location_id.name)
                 if not rec.location_dest_id:
                     rec.location_dest_id = rec.operation_id.default_dest_location_id
                     _logger.warning("Auto-set Destination Location from operation: %s", rec.location_dest_id.name)

    @api.model
    def create(self, vals):
        if 'product_id' in vals and 'operation_id' in vals:
            operation = self.env['custom.inventory.operation'].browse(vals['operation_id'])

            if ('location_id' not in vals or not vals['location_id']) and operation.default_source_location_id:
                vals['location_id'] = operation.default_source_location_id.id

            if ('location_dest_id' not in vals or not vals['location_dest_id']) and operation.default_dest_location_id:
                vals['location_dest_id'] = operation.default_dest_location_id.id

        return super().create(vals)

    def write(self, vals):
        for rec in self:
            operation = rec.operation_id
            if 'operation_id' in vals:
                operation = self.env['custom.inventory.operation'].browse(vals['operation_id'])

            if ('location_id' not in vals or not vals.get(
                    'location_id')) and not rec.location_id and operation.default_source_location_id:
                vals['location_id'] = operation.default_source_location_id.id

            if ('location_dest_id' not in vals or not vals.get(
                    'location_dest_id')) and not rec.location_dest_id and operation.default_dest_location_id:
                vals['location_dest_id'] = operation.default_dest_location_id.id



        return super().write(vals)


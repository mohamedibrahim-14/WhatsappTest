from odoo import models, fields, api



class CustomStockLocation(models.Model):
    _name = 'custom.inventory.location'
    _description = 'Custom Inventory Location'

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Location Code must be unique!')
    ]

    name = fields.Char(string='Location Name', required=True)
    code = fields.Char(string='Location Code', required=True)
    manager_ids = fields.Many2many(
        'res.users',
        'custom_location_manager_rel',
        'location_id',
        'user_id',
        string='Location Managers'
    )
    current_asset_count = fields.Integer(
        string='Current Asset Count', compute='_compute_current_asset_count', store=True
    )
    active = fields.Boolean(string='Active', default=True)
    address = fields.Text(string='Address')
    notes = fields.Text(string='Notes')
    assigned_product_ids = fields.One2many(
        'custom.inventory.product',
        'location_id',
        string="Assigned Products"
    )
    move_source_ids = fields.One2many(
        'custom.inventory.move',
        'location_id',
        string='Outgoing Movements'
    )

    move_dest_ids = fields.One2many(
        'custom.inventory.move',
        'location_dest_id',
        string='Incoming Movements'
    )

    analytic_account_asset=fields.Many2one('account.analytic.account',string="Analytic Account")
    maintenance_location=fields.Boolean(string='Maintenance Location')

    @api.depends('assigned_product_ids')
    def _compute_current_asset_count(self):
        for record in self:
            record.current_asset_count = len(record.assigned_product_ids)




class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    inventory_location_ids = fields.One2many(
        'custom.inventory.location',
        'analytic_account_asset',
        string='Assets Transfer'
    )
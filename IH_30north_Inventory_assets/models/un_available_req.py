from odoo import models, fields

class UnavailableInventoryRequest(models.Model):
    _name = 'custom.inventory.unavailable'
    _description = 'Unavailable Inventory Request'

    request_id = fields.Many2one('requests.inventory', string='Inventory Request')
    product_id = fields.Many2one('custom.inventory.product', string='Product')
    asset_type = fields.Many2one('assets.type', string='Asset Type')
    unavailable_quantity = fields.Integer(string='Unavailable Quantity')
    requested_location_id = fields.Many2one('custom.inventory.location', string='Requested Location')
    requested_by = fields.Many2one('res.users', string='Requested By')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('purchased', 'Purchased'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled')
    ], default='pending', string='Status')
    date = fields.Date(string='Date', default=fields.Date.today)
    note = fields.Text(string='Note')

    def action_mark_purchased(self):
        for rec in self:
            rec.state = 'purchased'

    def action_open_receive_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.receive.asset',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_type': self.asset_type.id if self.asset_type else False,
                'default_location_id': self.requested_location_id.id if self.requested_location_id else False,
                'default_request_id': self.id,
                'default_category_name': self.asset_type.category_name.id if self.asset_type and self.asset_type.category_name else False,
            }
        }

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_mark_pending(self):
        for rec in self:
            rec.state = 'pending'


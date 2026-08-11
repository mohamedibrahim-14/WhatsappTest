from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class WizardReceiveAsset(models.TransientModel):
    _name = 'wizard.receive.asset'
    _description = 'Receive Asset Wizard'

    asset_name = fields.Char(string='Asset Name', required=True)
    asset_type = fields.Many2one('assets.type', string='Asset Type', required=True)
    serial_number = fields.Char(string='Serial Number')
    asset_status = fields.Selection([
        ('active', 'Active'),
        ('transferable', 'Transferable'),
        ('disposed', 'Disposed')
    ], string='Asset Status', default='active')
    default_code = fields.Char(string='Internal Reference')
    category_name = fields.Many2one('custom.inventory.category', string='Category', readonly=True)

    location_id = fields.Many2one('custom.inventory.location', string='Location')
    request_id = fields.Many2one('custom.inventory.unavailable', string='Request')

    def action_confirm_create_asset(self):
        self.ensure_one()

        self.env['custom.inventory.product'].create({
            'name': self.asset_name,
            'asset_name': self.asset_type.id,
            'track_serial': self.serial_number,
            'default_code': self.default_code,
            'asset_status': self.asset_status,
            'category_id': self.category_name.id,
            'location_id': self.location_id.id,
        })

        quant = self.env['custom.inventory.quant'].search([
            ('asset_type', '=', self.asset_type.id),
            ('location_id', '=', self.location_id.id),
            ('lines_requests_id', '=', self.request_id.request_id.id)
        ], limit=1)

        if quant:
            if quant.un_availability_no > 0:
                quant.un_availability_no -= 1
                quant.availability_no += 1
        else:
            _logger.warning("No matching quant found.")

        self.request_id.state = 'received'

        # ✅ Check if all related unavailable lines are received
        request = self.request_id.request_id
        unavailables = self.env['custom.inventory.unavailable'].search([
            ('request_id', '=', request.id)
        ])

        if all(u.state == 'received' for u in unavailables):

            _logger.warning(f"Request {request.name} is now marked as DONE — all unavailable lines received.")
        else:
            _logger.warning(f"Request {request.name} is still pending — not all unavailable lines are received.")

        return {'type': 'ir.actions.act_window_close'}


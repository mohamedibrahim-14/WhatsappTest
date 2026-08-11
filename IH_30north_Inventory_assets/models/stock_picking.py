from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CustomStockPicking(models.Model):
    _name = 'custom.inventory.picking'
    _description = 'Custom Inventory Picking'

    name = fields.Char(string='Operation Name')
    default_source_location_id = fields.Many2one('custom.inventory.location', string='Source Location')
    sequence_code = fields.Many2one('ir.sequence', string='Operation Code')
    sequence_preview = fields.Char(string='Sequence Preview', compute='_compute_preview', readonly=True)
    operation_type=fields.Selection([('transfer','Transfer'),('return','Return')],string='Operation Type')
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')


    # @api.onchange('sequence_code')
    # def _onchange_sequence_code(self):
    #     for rec in self:
    #         if rec.sequence_code:
    #             rec.sequence_preview = rec.sequence_code._next()
    #         else:
    #             rec.sequence_preview = False

    @api.depends('default_source_location_id')
    def _compute_preview(self):
        """Show next available sequence per location."""
        for rec in self:
            if rec.default_source_location_id:
                prefix = rec.default_source_location_id.display_name or 'LOC'
                # Count how many records for this location to determine the next number
                existing = self.search_count([('default_source_location_id', '=', rec.default_source_location_id.id)])
                next_number = str(existing + 1).zfill(3)
                rec.sequence_preview = f"{prefix}/{next_number}"
            else:
                rec.sequence_preview = ''

    @api.model
    def create(self, vals):
        """Generate custom sequence per location."""
        rec = super(CustomStockPicking, self).create(vals)

        if rec.default_source_location_id:
            prefix = rec.default_source_location_id.display_name or 'LOC'
            existing = self.search_count([
                ('default_source_location_id', '=', rec.default_source_location_id.id),
                ('id', '<=', rec.id)
            ])
            seq_number = str(existing).zfill(3)
            rec.name = f"{prefix}/{seq_number}"
        else:
            rec.name = "UNKNOWN/001"

        return rec

    def get_action_related_operations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related Operations',
            'res_model': 'custom.inventory.operation',
            'view_mode': 'tree,form',
            'domain': [('code', '=', self.id)],
            'context': {
                **self.env.context,
                'default_code': self.id,  # prefill the code field
                'default_operation_type': 'in',  # set default operation type
                'default_source_location_id': self.default_source_location_id.id,  # example extra field
            },
            'target': 'current',
        }

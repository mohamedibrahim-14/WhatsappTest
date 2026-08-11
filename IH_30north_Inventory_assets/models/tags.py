from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class AssetTag(models.Model):
    _name = 'ih.asset.tag'
    _description = 'Asset Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color Index', default=0)

    @api.model
    def create(self, vals):
        if 'name' in vals:
            vals['name'] = vals['name'].strip()
        return super(AssetTag, self).create(vals)



    @api.constrains('name')
    def _check_name_unique(self):
        for record in self:
            if record.name:
                existing_tag = self.env['ih.asset.tag'].search([
                    ('name', '=', record.name),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing_tag:
                    raise ValidationError(f"Tag name '{record.name}' must be unique.")
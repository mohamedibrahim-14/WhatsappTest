from odoo import models, fields

class CustomProductCategory(models.Model):
    _name = 'assets.type'

    name = fields.Char(string='Asset Type Name')
    category_name=fields.Many2one('custom.inventory.category',string='Category')



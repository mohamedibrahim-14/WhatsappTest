from odoo import models, fields

class CustomProductCategory(models.Model):
    _name = 'custom.inventory.parent.category'
    _description = 'Product Parent Category'

    name = fields.Char(string='Parent Category Name', required=True)
    code = fields.Char(string='Code')

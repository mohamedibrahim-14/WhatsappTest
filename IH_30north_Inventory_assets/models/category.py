
from odoo import models, fields

class CustomProductCategory(models.Model):
    _name = 'custom.inventory.category'
    _description = 'Product Category'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    parent_category_name = fields.Many2one('custom.inventory.parent.category',string='Parent Category')
    category_color= fields.Char(string='Category Color',store=True)

from odoo import models, fields

class EventEventInherit(models.Model):
    _inherit = 'event.event'

    registration_mode = fields.Selection([
        ('register_only', 'Register Only'),
        ('register_pay', 'Register & Pay'),
    ], string='Registration Mode', default='register_pay',
       help="Choose whether participants can only register or register and pay for tickets.")

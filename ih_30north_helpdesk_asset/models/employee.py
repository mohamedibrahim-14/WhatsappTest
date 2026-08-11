from odoo import models, fields


class HrEmployeeHelpdesk(models.Model):
    _inherit = 'hr.employee'

    filter_it = fields.Boolean(string='IT Team', default=False)
    filter_maintenance = fields.Boolean(string='Maintenance Team', default=False)


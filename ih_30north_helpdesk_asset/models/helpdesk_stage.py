from odoo import models, fields


class HelpdeskStage(models.Model):
    _inherit = 'helpdesk.stage'

    is_draft          = fields.Boolean(string="Is Draft Stage")
    is_submit         = fields.Boolean(string="Is Submit Stage")
    is_assigned       = fields.Boolean(string="Is Assigned Stage")
    is_checking       = fields.Boolean(string="Is Checking Stage")
    is_maintenance    = fields.Boolean(string="Is Maintenance Approval Stage")
    is_waiting_warehouse_availability = fields.Boolean(string="Is Waiting for Warehouse Availability Stage")
    is_sp_installed = fields.Boolean('Is SP Installed')
    is_waiting_done = fields.Boolean(string='Is Waiting for Done Stage')
    is_done= fields.Boolean(string="Is Done Stage")
    is_cancel=fields.Boolean(string="Is Cancel Stage")
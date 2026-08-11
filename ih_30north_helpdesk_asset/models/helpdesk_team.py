from odoo import models, fields


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    warehouse_user_ids = fields.Many2many(
        'res.users',
        'helpdesk_team_warehouse_user_rel',
        'team_id',
        'user_id',
        string='Warehouse Approvers',
        domain="[('share', '=', False)]",
        help="Warehouse users notified to confirm spare parts availability for "
             "this team. Leave empty to fall back to every member of the "
             "Warehouse Manager group.",
    )

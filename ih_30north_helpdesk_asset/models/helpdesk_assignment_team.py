from odoo import models, fields, api


class HelpdeskAssignmentTeam(models.Model):
    _name = 'helpdesk.assignment.team'
    _description = 'Helpdesk Assignment Team'
    _order = 'sequence, name'

    name = fields.Char(string='Team Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    employee_ids = fields.Many2many(
        'hr.employee',
        'helpdesk_assignment_team_employee_rel',
        'team_id',
        'employee_id',
        string='Employees',
        help="Employees belonging to this team. Their linked users receive the "
             "ticket assignment and the notification email.",
    )
    user_ids = fields.Many2many(
        'res.users',
        string='Users',
        compute='_compute_user_ids',
        help="Users behind the team employees.",
    )
    employee_count = fields.Integer(compute='_compute_employee_count')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A team with this name already exists.'),
    ]

    @api.depends('employee_ids.user_id')
    def _compute_user_ids(self):
        for team in self:
            team.user_ids = team.employee_ids.user_id.filtered(lambda u: u.active)

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for team in self:
            team.employee_count = len(team.employee_ids)

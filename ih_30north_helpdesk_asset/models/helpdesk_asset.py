from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError
from datetime import timedelta

class helpdeskproduct(models.Model):
    _inherit = 'helpdesk.ticket'

    asset_location_helpdesk = fields.Many2one('custom.inventory.location', 'Asset Location')
    asset_category_helpdesk = fields.Many2one('custom.inventory.category', 'Asset Category', domain="asset_category_helpdesk_domain")
    asset_category_helpdesk_domain = fields.Char(compute='_compute_asset_category_domain', store=False)
    assets_helpdesk = fields.Many2one('custom.inventory.product','Assets',domain="assets_helpdesk_domain",)
    assets_helpdesk_domain = fields.Char(compute='_compute_assets_domain', store=False)
    asset_tags_helpdesk = fields.Many2many('ih.asset.tag', string='Asset Tags', related='assets_helpdesk.asset_tags')
    employee_helpdesk = fields.Many2one('hr.employee','Technician',domain="employee_helpdesk_domain",)
    employee_helpdesk_domain = fields.Char(compute='_compute_employee_domain',store=False)
    states=fields.Selection([('draft','Draft'),('submit','Submit'),('checking','Checking'),
                             ('maintenance_m_approved','Maintenance Manager Approval'),('finance_approver','Finance Approved')
                            ,('done','Done'),('cancel','Cancel')],default='draft')
    assignment_team = fields.Many2one(
        'helpdesk.assignment.team', string="Assign To Team", tracking=True,
        default=lambda self: self._get_team_of_current_user().id,)
    spare_parts = fields.Boolean('Spare Parts')
    # checking = fields.Boolean(string='Checking',required=True)
    spare_name = fields.Char('Spare Part Name')
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "helpdesk_ticket_ir_attachments_rel",
        "ticket_id",
        "attachment_id",
        string="Attachments",
        help="Attachments related to this ticket.",
        domain="[('res_model', '=', 'helpdesk.ticket'), ('res_id', '=', id)]",
    )
    is_stage_draft = fields.Boolean(compute='_compute_stage_flags')
    is_stage_submit = fields.Boolean(compute='_compute_stage_flags')
    is_stage_assigned = fields.Boolean(compute='_compute_stage_flags')
    is_stage_checking = fields.Boolean(compute='_compute_stage_flags')
    is_stage_maintenance = fields.Boolean(compute='_compute_stage_flags')
    is_stage_waiting_warehouse_availability = fields.Boolean(compute='_compute_stage_flags')
    is_stage_waiting_done = fields.Boolean(compute='_compute_stage_flags')
    is_stage_done = fields.Boolean(compute='_compute_stage_flags')
    is_stage_cancel = fields.Boolean(compute='_compute_stage_flags')
    # is_stage_waiting_sp_approval = fields.Boolean(compute='_compute_stage_flags')
    is_stage_sp_installed = fields.Boolean(compute='_compute_stage_flags')
    kanban_state = fields.Selection(selection_add=[('done_closed', 'Black')], ondelete={'done_closed': 'set default'})
    kanban_state_label = fields.Char(compute='_compute_kanban_state_label', string='Kanban State Label', tracking=True)

    legend_closed = fields.Char(
        related='stage_id.legend_closed',
        string='Kanban Closed Explanation',
        readonly=True,
        related_sudo=False
    )
    # Expose legend_done_closed so the state_selection widget can auto-pick the label
    legend_done_closed = fields.Char(
        related='stage_id.legend_closed',
        string='Kanban Done Closed Explanation',
        readonly=True,
        related_sudo=False
    )

    @api.depends('stage_id', 'kanban_state', 'legend_closed')
    def _compute_kanban_state_label(self):
        for ticket in self:
            if ticket.kanban_state == 'normal':
                ticket.kanban_state_label = ticket.legend_normal
            elif ticket.kanban_state == 'blocked':
                ticket.kanban_state_label = ticket.legend_blocked
            elif ticket.kanban_state == 'done_closed':
                ticket.kanban_state_label = ticket.legend_closed or 'Black'
            else:
                ticket.kanban_state_label = ticket.legend_done

    @api.depends('stage_id')
    def _compute_stage_flags(self):
        for rec in self:
            stage = rec.stage_id
            rec.is_stage_submit = stage.is_submit if stage else False
            rec.is_stage_assigned = stage.is_assigned if stage else False
            rec.is_stage_checking = stage.is_checking if stage else False
            rec.is_stage_maintenance = stage.is_maintenance if stage else False
            rec.is_stage_waiting_warehouse_availability = stage.is_waiting_warehouse_availability if stage else False
            rec.is_stage_waiting_done = stage.is_waiting_done if stage else False
            rec.is_stage_done = stage.is_done if stage else False
            rec.is_stage_cancel = stage.is_cancel if stage else False
            rec.is_stage_sp_installed = stage.is_sp_installed if stage else False
            # Draft is explicit via the stage flag, but a stage with no flag at
            # all (and a ticket with no stage yet) still counts as Draft.
            rec.is_stage_draft = stage.is_draft if stage else True
            if not rec.is_stage_draft and stage:
                rec.is_stage_draft = not any((
                    rec.is_stage_submit,
                    rec.is_stage_assigned,
                    rec.is_stage_checking,
                    rec.is_stage_maintenance,
                    rec.is_stage_waiting_warehouse_availability,
                    rec.is_stage_waiting_done,
                    rec.is_stage_done,
                    rec.is_stage_cancel,
                    rec.is_stage_sp_installed,
                ))
    def _get_stage_by_flag(self, flag_field):
        """Find the stage carrying a specific boolean flag.

        The cycle is driven by the flags, not by stage names or sequences, and each
        team configures its own stages. So prefer a flagged stage belonging to this
        ticket's team: writing a stage that is not in team_id.stage_ids is unsafe,
        because helpdesk.ticket.stage_id is a computed stored field that resets to
        the team default whenever team_id is written. Fall back to a global lookup
        when the team has no stage for the flag, which keeps single-cycle databases
        (where the flagged stages are not linked to any team) working as before.
        """
        stage = self.env['helpdesk.stage']
        team = self[:1].team_id
        if team:
            stage = team.stage_ids.filtered(
                lambda st: st[flag_field]
            ).sorted(lambda st: (st.sequence, st.id))[:1]
        if not stage:
            stage = self.env['helpdesk.stage'].search(
                [(flag_field, '=', True)], order='sequence, id', limit=1
            )
        if not stage:
            raise ValidationError(f"No stage configured with {flag_field} = True")
        return stage

    def action_submit(self):
        for rec in self:
            if not rec.stage_id.is_submit and rec.stage_id:
                pass  # already passed submit
            rec.stage_id = rec._get_stage_by_flag('is_submit')
        self._send_activity_to_group(
            "ih_30north_helpdesk_asset.approval_cycle_maintenance_manager",
            summary="Ticket Waiting Assignment",
            note="Kindly assign the ticket to a team and a technician"
        )

    def action_assign(self):
        """Maintenance manager assigns the team and technician."""
        for rec in self:
            if not rec.assignment_team:
                raise ValidationError("Please set the team before assigning the ticket.")
            if not rec.employee_helpdesk:
                raise ValidationError("Please set the technician before assigning the ticket.")

            rec.stage_id = rec._get_stage_by_flag('is_assigned')

            technician_user = rec.employee_helpdesk.user_id.filtered(lambda u: u.active)
            if technician_user:
                rec.user_id = technician_user[0].id
                rec._notify_users(
                    technician_user,
                    summary="Ticket Assigned To You",
                    note="You have been assigned to this ticket — Kindly confirm it",
                )
            else:
                _logger.warning(
                    "Technician '%s' has no active user, cannot notify (ticket %s).",
                    rec.employee_helpdesk.display_name, rec.id,
                )

    def action_warehouse_received(self):
        """Warehouse confirmed the spare parts are available."""
        for rec in self:
            rec.stage_id = rec._get_stage_by_flag('is_sp_installed')

        self._send_activity_to_group(
            "ih_30north_helpdesk_asset.approval_cycle_maintenance_manager",
            summary="Spare Parts Ready for Installation",
            note="Spare parts are available — Kindly install the spare parts"
        )

    is_current_user_technician = fields.Boolean(
        compute='_compute_is_current_user_technician',
        compute_sudo=False,
    )

    @api.depends_context('uid')
    @api.depends('employee_helpdesk')
    def _compute_is_current_user_technician(self):
        """True for the technician assigned to this ticket.

        Not used by the Confirm button, which is gated by the Technician Confirm
        group. Kept so the button can additionally be limited to the assigned
        technician: add `or not is_current_user_technician` to its invisible.
        """
        for rec in self:
            rec.is_current_user_technician = (
                self.env.user in rec.employee_helpdesk.user_id
            )

    def action_checking(self):
        """Technician confirmed the assignment."""
        for rec in self:
            rec.stage_id = rec._get_stage_by_flag('is_checking')
        self._send_activity_to_group(
            "ih_30north_helpdesk_asset.approval_cycle_maintenance_manager",
            summary="Ticket Approval",
            note="Kindly check the ticket and approve or refuse it"
        )

    def action_maintenance_approve(self):
        for rec in self:
            if rec.spare_parts:
                # ✅ spare parts → Waiting for Warehouse Availability
                rec.stage_id = rec._get_stage_by_flag('is_waiting_warehouse_availability')
                rec._notify_warehouse_users(
                    summary="Check Spare Parts Availability",
                    note="Spare parts required — Kindly check the availability"
                )
            else:
                # ✅ no spare parts → Waiting for Done
                rec.stage_id = rec._get_stage_by_flag('is_waiting_done')
                rec._send_activity_to_group(
                    "ih_30north_helpdesk_asset.approval_cycle_branch_manager",
                    summary="Waiting to Close Ticket",
                    note="No spare parts required — Kindly close the ticket"
                )

    def action_sp_installed(self):
        """Maintenance installed the parts — hand over to the branch manager."""
        for rec in self:
            rec.stage_id = rec._get_stage_by_flag('is_waiting_done')
        self._send_activity_to_group(
            "ih_30north_helpdesk_asset.approval_cycle_branch_manager",
            summary="Close the ticket",
            note="Spare parts installed — Kindly close the ticket"
        )

    def action_done(self):
        for rec in self:
            rec.stage_id = rec._get_stage_by_flag('is_done')
            rec.kanban_state = 'done_closed'

    def action_cancel(self):
        for rec in self:
            rec.stage_id = rec._get_stage_by_flag('is_cancel')

    def action_reset_draft(self):
        """Go back to the first stage (Draft)"""
        for rec in self:
            first_stage = self.env['helpdesk.stage'].search(
                [], order='sequence asc', limit=1
            )
            if first_stage:
                rec.stage_id = first_stage

    def _send_activity_to_group(self, group_xmlid, summary="New Task", note=""):
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not group:
            return

        self._notify_users(
            group.users.filtered(lambda u: u.active), summary=summary, note=note
        )

    def _notify_users(self, users, summary="New Task", note=""):
        """Give every user a To-Do and email them about each ticket in self."""
        if not users:
            return

        self._send_activity_to_users(users, summary=summary, note=note)
        self._email_users(users, summary=summary, note=note)

    def _send_activity_to_users(self, users, summary="New Task", note=""):
        """Create one To-Do per user on every ticket in self."""
        if not users:
            return

        activity_type = self.env.ref('mail.mail_activity_data_todo')
        model_id = self.env['ir.model']._get_id('helpdesk.ticket')

        for rec in self:
            for user in users:
                self.env['mail.activity'].create({
                    'res_id': rec.id,
                    'res_model_id': model_id,
                    'user_id': user.id,
                    'activity_type_id': activity_type.id,
                    'summary': summary,
                    'note': note,
                })

    def _email_users(self, users, summary="New Task", note=""):
        """Post on the ticket and email the given users.

        Recipients are passed as partner_ids rather than subscribed, so a step's
        approvers get this one message without following every later update on
        the ticket.
        """
        partners = users.partner_id.filtered(lambda p: p.email)
        if not partners:
            _logger.warning(
                "No email address among %d recipient(s) for '%s'.",
                len(users), summary,
            )
            return

        # mail_notify_force_send=False queues the mails for the "Mail: Email
        # Queue Manager" cron instead of opening an SMTP connection inside the
        # request. Without it, a slow or unreachable mail server makes every
        # button click wait for the timeout.
        for rec in self.with_context(mail_notify_force_send=False):
            rec.message_post_with_source(
                'ih_30north_helpdesk_asset.mail_notification_cycle_step',
                render_values={'summary': summary, 'note': note},
                subject="%s: %s" % (summary, rec.name or ''),
                partner_ids=partners.ids,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
            )

    def _send_activity_to_followers(self, summary="New Task", note="", activity_xmlid='mail.mail_activity_data_todo'):
        """Create one activity per internal follower of the ticket.

        mail.activity.user_id is a single user, so an activity cannot fan out
        on its own — one record per follower is the only way.
        Use 'mail.mail_activity_data_call' or 'mail.mail_activity_data_email'
        for a Call or Email activity instead of a To-Do.
        """
        activity_type = self.env.ref(activity_xmlid, raise_if_not_found=False)
        if not activity_type:
            _logger.warning("Activity type not found: %s", activity_xmlid)
            return

        model_id = self.env['ir.model']._get_id('helpdesk.ticket')

        for rec in self:
            # share=True are portal/customer followers — they have no Odoo backend.
            users = rec.message_partner_ids.user_ids.filtered(
                lambda u: u.active and not u.share
            )
            for user in users:
                self.env['mail.activity'].create({
                    'res_id': rec.id,
                    'res_model_id': model_id,
                    'user_id': user.id,
                    'activity_type_id': activity_type.id,
                    'summary': summary,
                    'note': note,
                })

    @api.depends('asset_location_helpdesk')
    def _compute_asset_category_domain(self):
        """Only offer categories that actually have an asset in that location."""
        for rec in self:
            if not rec.asset_location_helpdesk:
                rec.asset_category_helpdesk_domain = "[]"
                continue

            categories = self.env['custom.inventory.product']._read_group(
                [('location_id', '=', rec.asset_location_helpdesk.id),
                 ('category_id', '!=', False)],
                groupby=['category_id'],
            )
            category_ids = [group[0].id for group in categories]
            rec.asset_category_helpdesk_domain = repr([('id', 'in', category_ids)])

    @api.depends('asset_location_helpdesk', 'asset_category_helpdesk')
    def _compute_assets_domain(self):
        """Narrow the asset list by location and/or category.

        Only the criteria actually filled in are applied, otherwise an empty
        location or category would match ('=', False) and hide every asset.
        """
        for rec in self:
            domain = []
            if rec.asset_location_helpdesk:
                domain.append(('location_id', '=', rec.asset_location_helpdesk.id))
            if rec.asset_category_helpdesk:
                domain.append(('category_id', '=', rec.asset_category_helpdesk.id))
            rec.assets_helpdesk_domain = repr(domain)

    @api.onchange('asset_location_helpdesk')
    def _onchange_asset_location(self):
        """Drop the category when the new location has no asset in it."""
        for rec in self:
            if not rec.asset_category_helpdesk or not rec.asset_location_helpdesk:
                continue
            has_asset = self.env['custom.inventory.product'].search_count([
                ('location_id', '=', rec.asset_location_helpdesk.id),
                ('category_id', '=', rec.asset_category_helpdesk.id),
            ], limit=1)
            if not has_asset:
                rec.asset_category_helpdesk = False

    @api.onchange('asset_location_helpdesk', 'asset_category_helpdesk')
    def _onchange_asset_filters(self):
        """Drop the selected asset once it no longer matches the new filters."""
        for rec in self:
            asset = rec.assets_helpdesk
            if not asset:
                continue
            if rec.asset_location_helpdesk and asset.location_id != rec.asset_location_helpdesk:
                rec.assets_helpdesk = False
            elif rec.asset_category_helpdesk and asset.category_id != rec.asset_category_helpdesk:
                rec.assets_helpdesk = False

    @api.depends('assignment_team')
    def _compute_employee_domain(self):
        """Offer only the technicians configured on the selected assignment team."""
        for rec in self:
            if rec.assignment_team:
                rec.employee_helpdesk_domain = repr(
                    [('id', 'in', rec.assignment_team.employee_ids.ids)]
                )
            else:
                rec.employee_helpdesk_domain = "[]"

    is_helpdesk_team_member = fields.Boolean(
        string='Is Helpdesk Team Member',
        compute='_compute_is_helpdesk_team_member',
        compute_sudo=False,
    )

    @api.depends_context('uid')
    def _compute_is_helpdesk_team_member(self):
        """True when the current user already belongs to one of the assignment teams."""
        member = bool(self._get_team_of_current_user())
        for rec in self:
            rec.is_helpdesk_team_member = member

    @api.model
    def _get_team_of_current_user(self):
        """Return the assignment team the current user is an employee of."""
        return self.env['helpdesk.assignment.team'].search(
            [('employee_ids.user_id', '=', self.env.uid)], limit=1
        )

    def _get_users_for_team(self, team):
        """Return every active user behind the team employees."""
        if not team:
            return self.env['res.users']
        return team.employee_ids.user_id.filtered(lambda u: u.active)

    def _get_warehouse_users(self):
        """Warehouse users to notify for this ticket.

        Configured per helpdesk team, falling back to the Warehouse Manager
        group so a team nobody configured still reaches somebody instead of
        leaving the ticket sitting there unnoticed.
        """
        self.ensure_one()
        users = self.team_id.warehouse_user_ids.filtered(lambda u: u.active)
        if users:
            return users

        group = self.env.ref(
            "ih_30north_helpdesk_asset.approval_cycle_warehouse",
            raise_if_not_found=False,
        )
        if not group:
            return self.env['res.users']

        _logger.warning(
            "No warehouse approver configured on team '%s' (ticket %s); "
            "falling back to the Warehouse Manager group.",
            self.team_id.display_name, self.id,
        )
        return group.users.filtered(lambda u: u.active)

    def _get_user_for_team(self, team):
        """Return one active user of the team.

        The current user wins when they belong to that team, so a team member
        creating a ticket keeps it instead of handing it to an arbitrary peer.
        """
        users = self._get_users_for_team(team)
        if self.env.user in users:
            return self.env.user
        return users[0] if users else False

    def _notify_warehouse_users(self, summary="New Task", note=""):
        """Give the team's warehouse approvers a To-Do and email them.

        Resolved per record because the approvers come from the ticket's own
        helpdesk team, unlike the group-based steps.
        """
        for rec in self:
            rec._notify_users(
                rec._get_warehouse_users(), summary=summary, note=note
            )

    def _notify_team_members(self):
        """Post a message on the ticket and email every member of the chosen team."""
        # Queued rather than sent inline — see _email_users.
        for rec in self.with_context(mail_notify_force_send=False):
            users = rec._get_users_for_team(rec.assignment_team)
            member_partners = users.partner_id.filtered(lambda p: p.email)

            # Followers of the helpdesk.team record itself. A res.groups has no
            # followers, so team_id is the only "team" that can supply them.
            team_follower_partners = rec.team_id.message_partner_ids.filtered(
                lambda p: p.email
            )

            partners = member_partners | team_follower_partners
            if not partners:
                _logger.warning(
                    "No team member or team follower with an email address for "
                    "team '%s' (ticket %s)",
                    rec.assignment_team.display_name, rec.id
                )
                continue

            # Make the assigned members followers so they keep receiving the
            # ticket updates. Team followers are only mailed, not subscribed —
            # otherwise every team follower would follow every ticket forever.
            if member_partners:
                rec.message_subscribe(partner_ids=member_partners.ids)

            team_label = rec.assignment_team.name or ''

            rec.message_post_with_source(
                'ih_30north_helpdesk_asset.mail_notification_cycle_step',
                render_values={
                    'summary': "Ticket assigned to %s" % team_label,
                    # Plain text: the template escapes with t-out, so any tag
                    # passed here would be printed literally.
                    'note': "This ticket has been assigned to the %s team." % team_label,
                },
                subject="Helpdesk Ticket assigned to %s team: %s" % (team_label, rec.name or ''),
                partner_ids=partners.ids,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
            )

    @api.onchange("assignment_team")
    def _onchange_assignment_team(self):
        for rec in self:
            # Drop a technician who is not part of the newly chosen team.
            if rec.employee_helpdesk and rec.employee_helpdesk not in rec.assignment_team.employee_ids:
                rec.employee_helpdesk = False

            if not rec.assignment_team:
                continue

            user = rec._get_user_for_team(rec.assignment_team)
            if user:
                rec.user_id = user.id

    def _assign_user_from_team(self):
        """Assign user_id based on assignment_team."""
        for rec in self:
            if not rec.assignment_team:
                continue

            user = rec._get_user_for_team(rec.assignment_team)
            if user:
                rec.user_id = user.id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._assign_user_from_team()
        records.filtered('assignment_team')._notify_team_members()
        return records

    def write(self, vals):
        res = super().write(vals)
        # Re-assign and notify only if team changed
        if "assignment_team" in vals:
            self._assign_user_from_team()
            self.filtered('assignment_team')._notify_team_members()
        return res

    @api.model
    def _auto_block_old_tickets(self):
        """
        Scheduled action:
        - Tickets created within 15 minutes → Ready (green)
        - Tickets created more than 15 minutes ago → Blocked (red)
        """
        threshold = fields.Datetime.now() - timedelta(minutes=15)

        # ✅ Within 15 minutes → Green (Ready)
        ready_tickets = self.search([
            ('kanban_state', '=', 'normal'),  # Still In Progress
            ('create_date', '>', threshold),  # Created LESS than 15 min ago
            ('kanban_state', '!=', 'done_closed')
        ])

        if ready_tickets:
            _logger.info(
                "Setting %d ticket(s) to Ready (within 15 minutes).",
                len(ready_tickets)
            )
            ready_tickets.write({'kanban_state': 'done'})  # green

        # 🔴 More than 15 minutes → Red (Blocked)
        blocked_tickets = self.search([
            ('kanban_state', 'in', ['normal', 'done']),  # In Progress or Ready
            ('create_date', '<=', threshold),  # Created 15+ min ago
            ('kanban_state', '!=', 'done_closed')
        ])

        if blocked_tickets:
            _logger.info(
                "Auto-blocking %d ticket(s) older than 15 minutes.",
                len(blocked_tickets)
            )
            blocked_tickets.write({'kanban_state': 'blocked'})

class HelpdeskStageExtended(models.Model):
    _inherit = 'helpdesk.stage'

    legend_closed = fields.Char(
        'Grey/Blue Kanban Label',
        default=lambda s: 'Closed',
        translate=True,
        required=True
    )

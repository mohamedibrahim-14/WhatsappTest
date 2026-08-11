from odoo import models, fields,api
import logging
_logger = logging.getLogger(__name__)

class CustomProductCategory(models.Model):
    _name = 'requests.inventory'
    _description = 'Asset Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ih.asset.mail.mixin']

    name = fields.Char(
        string='Request Reference',
        required=True,
        readonly=True,
        default='New'
    )

    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.context_today,
        required=True,
        readonly=True,
    )

    location_id = fields.Many2one(
        'custom.inventory.location',
        string='Location',
        required=True
    )

    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('validate', 'Validate '),
        ('Inventory_Validation', 'Confirm Availability'),
        ('approved','Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many(
        'custom.inventory.quant',
        'lines_requests_id',
        string='Request Lines'
    )

    current_asset_count_requests = fields.Integer(
        string='Current Asset Count', compute='_compute_current_asset_count_requests', store=True
    )

    notes = fields.Text(string='Request REF')
    operation_ids = fields.One2many('custom.inventory.operation', 'request_id', string='Related Movements')
    operation_count = fields.Integer(string='Movements Count', compute='_compute_operation_count')


    def _compute_operation_count(self):
        for rec in self:
            rec.operation_count = len(rec.operation_ids)

    def action_view_movements(self):
        self.ensure_one()
        return {
            'name': 'Movements',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'custom.inventory.operation',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id},
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.request') or 'New'

        record = super().create(vals)

        # If state is draft, notify group users by email.
        if record.state == 'draft':
            group = self.env.ref('IH_30north_Inventory_assets.group_custom_asset_SCM', raise_if_not_found=False)
            if group:
                record._send_email_to_users(
                    group.users,
                    subject='New Asset Request (Draft)',
                    body_html=f'<p>A new asset request <b>{record.name}</b> has been created and is currently in Draft state.</p>',
                )

        return record

    @api.depends('line_ids')
    def _compute_current_asset_count_requests(self):
        for rec in self:
            rec.current_asset_count_requests = len(rec.line_ids)

    def action_validate(self):
        _logger.warning("🚀 action_validate triggered for records: %s", self.ids)

        group = self.env.ref(
            'IH_30north_Inventory_assets.group_confirm_availability',
            raise_if_not_found=False
        )

        if not group:
            _logger.warning("❌ Group not found: group_confirm_availability")
        else:
            _logger.warning("✅ Group found: %s", group.name)

        for rec in self:
            _logger.warning("➡ Processing record ID=%s state=%s", rec.id, rec.state)

            # Update state
            rec.state = 'validate'
            _logger.warning("✅ State updated to 'validate' for record ID=%s", rec.id)

            # No-op in email mode, kept for workflow compatibility.
            rec._close_related_activities()
            _logger.warning("📧 Activity closure skipped (email mode) for record ID=%s", rec.id)

            if not group:
                continue

            _logger.warning("👥 Users in group: %s", group.users.mapped('login'))

            # _send_email_to_users never raises; it logs a MAIL summary line
            # with the per-recipient outcome (sent / queued / skipped / failed).
            rec._send_email_to_users(
                group.users,
                subject='Asset Request is waiting for confirmation',
                body_html='<p>Availability check required.</p>',
            )

    def action_confirm_inventory(self):
        for rec in self:
            rec.state = 'Inventory_Validation'
            group = self.env.ref('IH_30north_Inventory_assets.group_approved')
            users = group.users
            rec._close_related_activities()
            rec._send_email_to_users(
                users,
                subject='Asset Request is waiting for approval',
                body_html=f'<p>Asset request <b>{rec.name}</b> is waiting for approval.</p>',
            )

    def _notify_purchasing(self, shortages):
        """Ask the Purchasing group to start the purchasing workflow.

        `shortages` is a list of (asset_type_name, missing_qty) for the lines
        that could not be served from stock.
        """
        self.ensure_one()

        group = self.env.ref(
            'IH_30north_Inventory_assets.group_purchasing',
            raise_if_not_found=False
        )
        if not group:
            _logger.error(
                "PURCHASING notify skipped | request=%s | group_purchasing not found "
                "(upgrade the module to load security/security_group.xml)",
                self.name
            )
            return

        if not group.users:
            _logger.warning(
                "PURCHASING notify skipped | request=%s | the Purchasing group has no members",
                self.name
            )
            return

        rows = ''.join(
            '<tr><td style="padding:4px 12px;border:1px solid #ddd;">%s</td>'
            '<td style="padding:4px 12px;border:1px solid #ddd;text-align:right;">%s</td></tr>'
            % (asset_type, qty)
            for asset_type, qty in shortages
        )

        body_html = f"""
            <p>Asset request <b>{self.name}</b> has been approved, but the
               following quantities are <b>not available in stock</b> and need
               to be purchased.</p>
            <table style="border-collapse:collapse;">
                <tr>
                    <th style="padding:4px 12px;border:1px solid #ddd;text-align:left;">Asset Type</th>
                    <th style="padding:4px 12px;border:1px solid #ddd;text-align:right;">Missing Qty</th>
                </tr>
                {rows}
            </table>
            <p>Requested location: <b>{self.location_id.name or ''}</b><br/>
               Requested by: <b>{self.requested_by.name or ''}</b></p>
            <p>Open <i>Requests &gt; Purchase Requests</i> to start the purchasing workflow.</p>
        """

        _logger.info(
            "PURCHASING notify | request=%s | shortages=%s",
            self.name, shortages
        )

        self._send_email_to_users(
            group.users,
            subject=f'Purchase needed for asset request {self.name}',
            body_html=body_html,
        )

    def action_approve(self):
        for rec in self:
            has_unavailable = False
            shortages = []

            for line in rec.line_ids:
                # ✅ Available items → create operation
                if line.availability_no > 0:
                    operation = self.env['custom.inventory.operation'].create({
                        'name': f'Movement for {rec.location_id.name}',
                        'default_dest_location_id': rec.location_id.id,
                        'requested_by': rec.requested_by.id,
                        'date': fields.Date.today(),
                        'request_id': rec.id,
                    })

                    _logger.warning(f"✅ Created operation {operation.name}")
                else:
                    _logger.warning("⚠️ Can't create operation as availability = 0")

                # ❌ Unavailable items → create unavailable records
                if line.un_availability_no > 0:
                    has_unavailable = True
                    shortages.append(
                        (line.asset_type.name or '-', line.un_availability_no)
                    )
                    for i in range(line.un_availability_no):
                        self.env['custom.inventory.unavailable'].create({
                            'request_id': rec.id,
                            'asset_type': line.asset_type.id,
                            'unavailable_quantity': 1,
                            'requested_location_id': rec.location_id.id,
                            'requested_by': rec.requested_by.id,
                            'date': fields.Date.today(),
                            'note': f"Auto-created: item {i + 1} of {line.un_availability_no}",
                        })

                        _logger.warning(
                            f"[{i + 1}/{line.un_availability_no}] "
                            f"Created unavailable record for asset type "
                            f"{line.asset_type.name} at location {rec.location_id.name}"
                        )

            # 🔄 change state
            rec.state = 'approved'

            # 🛒 unavailable quantities -> hand over to Purchasing
            if has_unavailable:
                rec._notify_purchasing(shortages)

            # 🔔 notify asset managers
            # 🔔 notify request creator only
            rec._close_related_activities()

            user = rec.requested_by

            if user:
                rec._send_email_to_users(
                    user,
                    subject='Asset Request Approved',
                    body_html='<p>Your asset request has been approved.</p>',
                )

                _logger.warning(
                    "📧 Email sent to request creator: %s (ID=%s)",
                    user.login, user.id
                )
            else:
                _logger.warning("⚠️ No requested_by user found for record %s", rec.id)

    def action_refuse(self):
        for rec in self:
            operations = self.env['custom.inventory.operation'].search([('request_id', '=', rec.id)])
            operations.unlink()
            _logger.warning(f"Deleted {len(operations)} operation(s) for request {rec.name}")

            unavailable_recs = self.env['custom.inventory.unavailable'].search([('request_id', '=', rec.id)])
            unavailable_recs.unlink()
            _logger.warning(f"Deleted {len(unavailable_recs)} unavailable record(s) for request {rec.name}")

            rec.state = 'rejected'
            rec._close_related_activities()

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

            # Get all users in the "Asset Manager" group
            group = self.env.ref('IH_30north_Inventory_assets.group_custom_asset_SCM')
            users = group.users

            rec._close_related_activities()


            rec._send_email_to_users(
                users,
                subject='Asset Request set to Draft',
                body_html='<p>A request has been set to Draft and requires your attention.</p>',
            )

    def _close_related_activities(self):
        # Kept to preserve existing workflow calls after switching from activities to email notifications.
        return True







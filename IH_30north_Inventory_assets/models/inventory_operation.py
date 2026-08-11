from odoo import models, fields,api
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class CustomOperationType(models.Model):
    _name = 'custom.inventory.operation'
    _description = 'Movements'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ih.asset.mail.mixin']

    sequence_code = fields.Char(string='Movement REF', readonly=True, tracking=True)
    name = fields.Char(string='Movement Description', required=True, tracking=True)
    code = fields.Many2one('custom.inventory.picking', string='Operation', tracking=True)
    default_source_location_id = fields.Many2one('custom.inventory.location', string='Source Location', tracking=True)
    default_dest_location_id = fields.Many2one('custom.inventory.location', string='Destination Location',tracking=True)
    move_ids = fields.One2many('custom.inventory.move', 'operation_id', string='Move Lines')
    state = fields.Selection([('draft', 'Draft'),('in_progress','In Progress'),('confirmed', 'Confirmed'),('cancel', 'Cancelled'),
    ], string='State', default='draft', tracking=True)
    requested_by = fields.Many2one('res.users', string='Requested By', readonly=True,default=lambda self: self.env.user)
    date=fields.Date(string='Date')
    notes = fields.Text(string='Notes')
    request_id = fields.Many2one('requests.inventory', string='Request REf')
    delivery_date=fields.Date(string='Actual Arrival Date')
    expected_date=fields.Date(string='Expected Date')
    report_count = fields.Integer(string="Report Count", compute="_compute_report_count")
    can_confirm = fields.Boolean(
        string="Can Confirm",
        compute="_compute_can_confirm",
        store=False
    )


    @api.constrains('move_ids')
    def _check_move_lines_not_empty(self):
        for rec in self:
            if not rec.move_ids:
                raise ValidationError("You must add at least one product line before saving.")

    @api.constrains('move_ids')
    def _check_duplicate_lines(self):
        for rec in self:
            seen = set()

            for line in rec.move_ids:
                key = (
                    line.product_id.id,
                    line.location_id.id,
                    line.location_dest_id.id
                )

                if key in seen:
                    raise ValidationError(
                        f"Duplicate line detected for product '{line.product_id.name}'."
                    )
                seen.add(key)

    def _compute_can_confirm(self):
        for operation in self:
            allowed = False
            for move in operation.move_ids:
                dest = move.location_dest_id
                _logger.warning(
                    "Checking Move ID: %s | Destination: %s | Managers: %s",
                    move.id,
                    dest.name if dest else "None",
                    [u.name for u in dest.manager_ids] if dest else []
                )
                if dest and self.env.user in dest.manager_ids:
                    allowed = True
                    break
            operation.can_confirm = allowed
            _logger.warning(
                "📌 can_confirm=%s for user '%s' | Operation: %s",
                allowed, self.env.user.name, operation.name
            )



    def _compute_report_count(self):
            for rec in self:
                rec.report_count = self.env['custom.inventory.reporting'].search_count([])

    def action_view_all_reports(self):
        return {
            'name': 'All Inventory Reports',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.inventory.reporting',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    @api.onchange('code')
    def _onchange_code(self):
        for rec in self:
            if rec.code:
                rec.default_source_location_id = rec.code.default_source_location_id

    @api.model
    def create(self, vals):
        """Auto-generate sequence_code by incrementing base sequence from picking."""
        rec = super(CustomOperationType, self).create(vals)

        if rec.code:
            base_prefix = rec.code.sequence_preview or rec.code.name or "NO-CODE"

            # Extract numeric part safely
            prefix, sep, num = base_prefix.rpartition('/')
            try:
                current_number = int(num)
            except ValueError:
                current_number = 0

            # Get next number (count of all operations + base number)
            count_existing = self.search_count([('code', '=', rec.code.id)])
            next_number = current_number + count_existing + 1

            # Build new code (e.g. cairo/002)
            rec.sequence_code = f"{prefix}/{str(next_number).zfill(3)}"
            rec.name = rec.sequence_code

        else:
            rec.sequence_code = "NO-CODE/001"

        return rec

    def action_confirm(self):
        for operation in self:
            _logger.warning("===== START confirming operation: %s (ID: %s) =====", operation.name, operation.id)

            for move in operation.move_ids:
                product = move.product_id
                source_location = move.location_id
                dest_location = move.location_dest_id

                if not dest_location:
                    raise UserError("Destination location is missing in one of the move lines.")

                    # ✅ Check manager permission
                if self.env.user not in dest_location.manager_ids:
                    raise UserError(
                        f"You are not allowed to confirm this movement.\n\n"
                        f"Only managers of destination location "
                        f"({dest_location.name}) can confirm it."
                    )

                # Close depreciation record for old location
                depreciation_source = self.env['asset.depreciation'].search([
                    ('asset_id', '=', product.id),
                    ('location_id', '=', source_location.id),
                    ('exit_date', '=', False)
                ], limit=1, order="entry_date desc")

                if depreciation_source:
                    depreciation_source.exit_date = fields.Datetime.now()
                    _logger.warning(
                        "Closed depreciation | Product: %s | From: %s",
                        product.name, source_location.name
                    )

                # Create new depreciation record
                self.env['asset.depreciation'].create({
                    'asset_id': product.id,
                    'location_id': dest_location.id,
                    'entry_date': fields.Datetime.now(),
                    'exit_date': False,
                })
                _logger.warning(
                    "Created depreciation | Product: %s | To: %s",
                    product.name, dest_location.name
                )

                # Update assigned products
                if product not in source_location.assigned_product_ids:
                    _logger.warning(
                        "Product %s NOT found in source location %s",
                        product.name, source_location.name
                    )
                    raise UserError(
                        f"Product '{product.name}' is not available in '{source_location.name}'"
                    )

                source_location.assigned_product_ids = [(3, product.id)]
                dest_location.assigned_product_ids = [(4, product.id)]

                # Update product location
                product.location_id = dest_location.id
                product.moved_by = operation.requested_by.id

                _logger.warning(
                    "Product %s moved | From: %s | To: %s",
                    product.name, source_location.name, dest_location.name
                )
                if dest_location.maintenance_location:
                    product.asset_status = 'under_maintenance'
                    _logger.warning(
                        "Product '%s' automatically set to UNDER MAINTENANCE | Location: %s",
                        product.name, dest_location.name
                    )
                else:
                    product.asset_status = 'transferable'
                    _logger.warning(
                        "Product '%s' automatically set to TRANSFERABLE | Location: %s",
                        product.name, dest_location.name
                    )

            # Finalize operation
            operation.state = 'confirmed'
            operation.delivery_date = fields.Datetime.now()

            _logger.warning(
                "Operation CONFIRMED | Ref: %s | By: %s",
                operation.name, operation.requested_by.name
            )

            # Create Activity for Warehouse Managers
            warehouse_group = self.env.ref(
                'IH_30north_Inventory_assets.group_warehouse_manager',
                raise_if_not_found=False
            )

            if not warehouse_group:
                _logger.warning("Warehouse Manager group NOT FOUND")
                continue

            users = warehouse_group.users.filtered(
                lambda u: u.active and u.id != self.env.user.id
            )

            if not users:
                _logger.warning("No active users found in Warehouse Manager group")

            operation._send_email_to_users(
                users,
                subject='Inventory Movement Confirmed',
                body_html=(
                    f"<p>Movement <b>{operation.name}</b> has been confirmed.</p>"
                    f"<p>Confirmed by: {operation.requested_by.name}</p>"
                ),
            )

            _logger.warning("===== END confirming operation: %s =====", operation.name)

        return True

    def action_refuse(self):
        for operation in self:
            _logger.info(f"===== Cancelling operation: {operation.name} =====")
            for move in operation.move_ids:
                product = move.product_id
                source_location = move.location_id
                dest_location = move.location_dest_id

                # ✅ Close depreciation record for new location
                depreciation_dest = self.env['asset.depreciation'].search([
                    ('asset_id', '=', product.id),
                    ('location_id', '=', dest_location.id),
                    ('exit_date', '=', False)
                ], limit=1, order="entry_date desc")
                if depreciation_dest:
                    depreciation_dest.exit_date = fields.Datetime.now()
                    _logger.info(f"📅 Closed depreciation record for '{product.name}' in '{dest_location.name}'")

                # ✅ Create new depreciation record for old location
                self.env['asset.depreciation'].create({
                    'asset_id': product.id,
                    'location_id': source_location.id,
                    'entry_date': fields.Datetime.now(),
                    'exit_date': False,
                })
                _logger.info(f"🔁 Created depreciation record for '{product.name}' in '{source_location.name}'")

                # Move product back
                if product in dest_location.assigned_product_ids:
                    dest_location.assigned_product_ids = [(3, product.id)]
                if product not in source_location.assigned_product_ids:
                    source_location.assigned_product_ids = [(4, product.id)]

                product.location_id = source_location.id

            operation.state = 'cancel'
            _logger.info(f"🚫 Operation '{operation.name}' cancelled.")
        return True

    def action_progress(self):
        for rec in self:
            rec.state='in_progress'


    def action_draft(self):
        for rec in self:
            rec.state='draft'


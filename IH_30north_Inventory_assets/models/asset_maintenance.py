from odoo import models, fields,api,_
from odoo.exceptions import UserError
import logging
from markupsafe import Markup
_logger = logging.getLogger(__name__)


class CustomProductCategory(models.Model):
    _name = 'asset.maintenance'
    _description = 'Asset Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(
        string='Request Reference',
        required=True,
        readonly=True,
        default=lambda self: _('New')
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
        required=True
    )
    note = fields.Text(string='Notes')
    priority = fields.Selection(
        [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        string='Priority',
        default='medium'
    )
    maintenance_responsible = fields.Many2one(
        'res.users',
        string='Responsible'
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('maintenance', 'Maintenance'),
            ('done', 'Done')
        ],
        string='Status',
        default='draft',
        tracking=True
    )
    cost = fields.Float(string='Cost',required=1)

    asset_id = fields.Many2one(
        'custom.inventory.product',
        string='Asset',
        required=True
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )

    @api.onchange('location_id')
    def _onchange_location_id(self):
        """Set analytic account from selected location."""
        for rec in self:
            if rec.location_id:
                rec.analytic_account_id = rec.location_id.analytic_account_asset
            else:
                rec.analytic_account_id = False

    def _schedule_activity_for_maintenance_users(self, summary, note):
        group = self.env.ref('IH_30north_Inventory_assets.group_maintenance_user',
            raise_if_not_found=False
        )

        if not group:
            _logger.warning("Maintenance User group not found")
            return

        partner_ids = group.users.filtered(lambda u: u.active and u.partner_id).mapped('partner_id').ids
        if not partner_ids:
            return

        for rec in self:
            _logger.warning(
                "Posting Maintenance Notification | Record: %s | Action: %s",
                rec.name, summary
            )

            rec.with_context(mail_notify_noemail=True).message_post(
                subject=summary,
                body=Markup(f"<p>{note}</p>"),
                partner_ids=partner_ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    # Only an asset in one of these states may be sent to maintenance.
    MAINTENANCE_ELIGIBLE_STATUS = ('active', 'transferable')

    def _set_asset_under_maintenance(self):
        """Flag the asset as "In Maintenance" as soon as the request is created.

        The asset must be Active or Transferable to be eligible; creating a
        request for an asset that is Disposed or already In Maintenance is
        rejected. Previously the status only changed once the asset was
        physically moved into a maintenance location (see
        inventory_operation.action_confirm), which left the asset showing as
        Active/Transferable in the meantime.

        sudo() because the requester may only have read access on the asset.
        """
        status_labels = dict(
            self.env['custom.inventory.product']._fields['asset_status'].selection
        )

        for rec in self:
            asset = rec.asset_id
            if not asset:
                _logger.warning(
                    "ASSET STATUS skipped | request=%s | reason=no asset on request", rec.name
                )
                continue

            previous = asset.asset_status
            if previous not in self.MAINTENANCE_ELIGIBLE_STATUS:
                _logger.warning(
                    "ASSET STATUS rejected | request=%s | asset=%s(%s) | status=%s "
                    "| only %s assets can be sent to maintenance",
                    rec.name, asset.name, asset.id, previous,
                    ', '.join(self.MAINTENANCE_ELIGIBLE_STATUS)
                )
                raise UserError(_(
                    'Asset "%(asset)s" is %(status)s, so it cannot be sent to maintenance.\n\n'
                    'Only assets that are Active or Transferable can have a '
                    'maintenance request created for them.',
                    asset=asset.name,
                    status=status_labels.get(previous, previous or _('not set')),
                ))

            asset.sudo().write({'asset_status': 'under_maintenance'})
            _logger.info(
                "ASSET STATUS set | request=%s | asset=%s(%s) | %s -> under_maintenance",
                rec.name, asset.name, asset.id, previous
            )

            rec.message_post(
                body=Markup(
                    _('Asset <b>%(asset)s</b> set to <b>In Maintenance</b> '
                      '(was: %(previous)s) on request creation.')
                ) % {
                    'asset': asset.name,
                    'previous': previous or _('not set'),
                }
            )

    # Auto-generate request name using a sequence
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'asset.maintenance.request'
                ) or _('New')

            # Auto-set analytic account if location is passed during create
            if vals.get('location_id') and not vals.get('analytic_account_id'):
                location = self.env['custom.inventory.location'].browse(vals['location_id'])
                vals['analytic_account_id'] = (
                    location.analytic_account_asset.id
                    if location.analytic_account_asset else False
                )

        records = super().create(vals_list)

        # Asset goes In Maintenance immediately, not on the asset movement.
        records._set_asset_under_maintenance()

        for record in records:
            record._schedule_activity_for_maintenance_users(
                summary='New Maintenance Request',
                note=f'Maintenance request <b>{record.name}</b> has been created.'
            )

        return records



    # Workflow actions
    def action_approve(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft requests can be approved."))
            rec.state = 'approved'
            rec._schedule_activity_for_maintenance_users(
                summary='Maintenance Request Approved',
                note=f'Maintenance request <b>{rec.name}</b> has been approved.'
            )

    def action_start_maintenance(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_("Only approved requests can start maintenance."))
            rec.state = 'maintenance'

            rec._schedule_activity_for_maintenance_users(
                summary='Maintenance Started',
                note=f'Maintenance request <b>{rec.name}</b> is now in progress.'
            )

    def action_done(self):
        for rec in self:
            if rec.state != 'maintenance':
                raise UserError(_("Only maintenance in progress can be marked done."))
            rec.state = 'done'

            rec._schedule_activity_for_maintenance_users(
                summary='Maintenance Completed',
                note=f'Maintenance request <b>{rec.name}</b> has been completed.'
            )

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'



from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class AssetDepreciation(models.Model):
    _name = 'asset.depreciation'
    _description = "Asset Depreciation by Location"

    asset_id = fields.Many2one(
        'custom.inventory.product',
        string="Asset",
        required=True
    )
    location_id = fields.Many2one(
        'custom.inventory.location',
        string="Location",
        required=True
    )
    entry_date = fields.Datetime(string="Entry Date")
    exit_date = fields.Datetime(string="Exit Date")
    months_in_location = fields.Integer(
        string="Months in Location",
        compute="_compute_months", store=True
    )
    depreciation_value = fields.Float(
        string="Depreciation Value",
        compute="_compute_depreciation", store=True
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Analytic Account",
        related="location_id.analytic_account_asset",
        store=True,
        readonly=True
    )

    @api.depends('entry_date', 'exit_date')
    def _compute_months(self):
        for rec in self:
            if rec.entry_date and rec.exit_date:
                delta = relativedelta(rec.exit_date, rec.entry_date)
                rec.months_in_location = delta.years * 12 + delta.months
                _logger.warning(f"[{rec.asset_id.name}] Months in location: {rec.months_in_location}")
            else:
                rec.months_in_location = 0

    @api.depends('months_in_location', 'asset_id')
    def _compute_depreciation(self):
        for rec in self:
            if rec.asset_id.asset_id:  # Linked to account.asset
                account_asset = rec.asset_id.asset_id

                # Get the monthly depreciation value from the related account.move
                move = self.env['account.move'].search([
                    ('asset_id', '=', account_asset.id),
                    ('state', '=', 'posted')
                ], limit=1)

                monthly_depreciation = move.depreciation_value or 0
                rec.depreciation_value = monthly_depreciation * rec.months_in_location

                _logger.warning(
                    f"[{rec.asset_id.name}] Depreciation: {rec.depreciation_value} "
                    f"(Monthly: {monthly_depreciation}, Months: {rec.months_in_location})"
                )
            else:
                rec.depreciation_value = 0
                _logger.warning(f"[{rec.asset_id.name}] No linked account.asset found.")

from odoo import models
import logging
_logger = logging.getLogger(__name__)

class AccountAssetAsset(models.Model):
    _inherit = 'account.move'

    def _prepare_move_for_asset_depreciation(self, vals):
        move_vals = super()._prepare_move_for_asset_depreciation(vals)
        asset = vals['asset_id']

        _logger.warning(
            f"[DEBUG] Preparing depreciation move for asset: {asset.name} (ID: {asset.id}) on date {vals['date']}")

        all_records = self.env['asset.depreciation'].search([
            ('asset_id.asset_id', '=', asset.id)
        ])
        if not all_records:
            _logger.warning(f"[DEBUG] No depreciation records found at all for asset {asset.name} (ID: {asset.id})")
        else:
            for rec in all_records:
                _logger.warning(
                    f"[DEBUG] Depreciation record: "
                    f"Location={rec.location_id.name}({rec.location_id.id}), "
                    f"Entry={rec.entry_date}, Exit={rec.exit_date}, "
                    f"Analytic={rec.location_id.analytic_account_asset and rec.location_id.analytic_account_asset.name or 'None'}"
                )

        _logger.warning(
            f"[DEBUG] Searching depreciation record for Asset={asset.id}, "
            f"Date={vals['date']}"
        )

        depreciation_record = self.env['asset.depreciation'].search([
            ('asset_id.asset_id', '=', asset.id),
            ('entry_date', '<=', vals['date']),
            '|',
            ('exit_date', '>=', vals['date']),
            ('exit_date', '=', False)
        ], order="entry_date desc", limit=1)

        _logger.warning(
            f"[DEBUG] Search domain used: [('asset_id', '=', {asset.id}), "
            f"('entry_date', '<=', {vals['date']}), "
            f"('|', ('exit_date', '>=', {vals['date']}), ('exit_date', '=', False))]"
        )
        if depreciation_record:
            _logger.warning(
                f"[DEBUG] Selected depreciation record: Location={depreciation_record.location_id.name} "
                f"(ID: {depreciation_record.location_id.id}) "
                f"from {depreciation_record.entry_date} to {depreciation_record.exit_date or 'Present'}"
            )
        else:
            _logger.warning(f"[DEBUG] No matching depreciation record found for date {vals['date']}")

        # analytic account
        analytic_account_id = False
        if depreciation_record and depreciation_record.location_id.analytic_account_asset:
            analytic_account_id = depreciation_record.location_id.analytic_account_asset.id
            _logger.warning(
                f"[DEBUG] Using Analytic Account: {depreciation_record.location_id.analytic_account_asset.name} "
                f"(ID: {analytic_account_id})"
            )
        else:
            _logger.warning("[DEBUG] No Analytic Account found for this location.")

        for _command, _id, line_vals in move_vals['line_ids']:
            if analytic_account_id:
                line_vals['analytic_distribution'] = {str(analytic_account_id): 100}
                _logger.warning(f"[DEBUG] Analytic distribution set for move line: {line_vals}")

        return move_vals

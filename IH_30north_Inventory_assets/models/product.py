from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)
from odoo import models, fields, api
import qrcode
import base64
from io import BytesIO
import qrcode, base64

class CustomProduct(models.Model):
    _name = 'custom.inventory.product'
    _description = 'Custom Inventory Product'

    category_id = fields.Many2one('custom.inventory.category',string='Category')
    parent_category_id = fields.Many2one('custom.inventory.parent.category',string='Parent Category')
    asset_name = fields.Many2one('assets.type',string='Assets Type')
    name = fields.Char(string='Asset Name')
    default_code = fields.Char(string='Internal Reference')
    description  = fields.Text(string='Description')
    track_serial = fields.Char(string='Serial Number')
    asset_value_ad = fields.Float( string='Asset Budget')
    asset_status = fields.Selection([('active','Active'),('transferable','Transferable'),('disposed','Disposed'),('under_maintenance','In Maintenance')],string='Asset Status',default='active')
    moved_by = fields.Many2one('res.users', string='Responsible ', default=lambda self: self.env.user)
    acquisition_date = fields.Datetime(string="Acquisition Date")
    move_history_ids = fields.One2many('custom.inventory.move', 'product_id', string='Movement History')
    location_id = fields.Many2one('custom.inventory.location', string='Location')
    asset_id = fields.Many2one('account.asset',string='Asset model')
    maintenance_ids = fields.One2many(
        'asset.maintenance',  # related model
        'asset_id',  # field in asset.maintenance pointing to this model
        string='Maintenance History'
    )
    qr_code = fields.Binary(string="QR Code", readonly=True)
    qr_url = fields.Char(string="QR URL", readonly=True)
    asset_tags = fields.Many2many(
        'ih.asset.tag',
        'asset_asset_tag_rel',  # relation table name in the database
        'asset_id',  # column for the current model
        'tag_id',  # column for ih.asset.tag
        string='Asset Tags'
    )
    move_count = fields.Integer(
        string='Movements', compute='_compute_move_count'
    )

    @api.depends('move_history_ids')
    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(rec.move_history_ids)

    def action_view_asset_movements(self):
        """Smart button: every movement line this asset went through.

        The list shows the parent movement (operation_id), so the movement
        itself is one click away.
        """
        self.ensure_one()
        _logger.info(
            "ASSET movements | asset=%s(%s) | count=%s",
            self.name, self.id, self.move_count
        )
        return {
            'type': 'ir.actions.act_window',
            'name': f"Movements of {self.name or ''}",
            'res_model': 'custom.inventory.move',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
                'search_default_product_id': self.id,
            },
        }

    @api.constrains('track_serial')
    def _check_track_serial_unique(self):
        for record in self:
            if record.track_serial:
                domain = [
                    ('track_serial', '=', record.track_serial),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain):
                    raise ValidationError("Serial Number must be unique!")

    def action_generate_missing_serial(self):
        for record in self:
            if not record.track_serial:
                record.track_serial = self.env['ir.sequence'].next_by_code(
                    'custom.inventory.product.serial'
                )

    def action_regenerate_qr(self):
        """Rebuild the QR image, overwriting the existing one.

        Needed after the QR payload changed from a text block to the plain
        /asset/info/<id> URL: assets created before that keep their old image,
        and action_generate_qr_single_record refuses to touch them because
        qr_code is already set. Works on a whole selection from the list view.
        """
        assets = self or self.browse(self.env.context.get('active_ids', []))
        _logger.info("[QR] Regenerating QR for %s asset(s): %s", len(assets), assets.ids)

        assets.generate_qr()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'QR Regenerated',
                'message': f'{len(assets)} QR code(s) regenerated. Reprint the labels.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_generate_qr_single_record(self):
        """
        Generate QR for the current record (form view single record).
        """
        record_id = self.env.context.get('active_id')
        if not record_id:
            return

        record = self.browse(record_id)

        if not record.qr_code:

            record.generate_qr()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'QR Code generated for {record.name}.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Info',
                    'message': 'This asset already has a QR Code.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

    @api.model
    def create(self, vals):
        record = super(CustomProduct, self).create(vals)
        record.generate_qr()
        return record

    def write(self, vals):
        res = super(CustomProduct, self).write(vals)
        if 'name' in vals or 'default_code' in vals or 'category_id' in vals:
            self.generate_qr()
        return res

    def generate_qr(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        _logger.info(f"[QR] Generating QR codes with base URL: {base_url}")

        for record in self:
            try:
                qr_url = f"{base_url}/asset/info/{record.id}"
                record.qr_url = qr_url

                _logger.debug(f"[QR] Asset ID: {record.id}")
                _logger.debug(f"[QR] QR URL: {qr_url}")

                # Encode the URL ONLY. A QR holding a bare URL is recognised as
                # a link by every phone camera, so scanning opens the asset page
                # directly. Anything else (a text block, a URL with a label in
                # front of it) is shown as plain text and has to be copied by
                # hand. The asset details the page used to embed are rendered by
                # /asset/info/<id> itself.
                qr_data = qr_url

                _logger.warning(f"[QR DATA] {qr_data}")
                _logger.debug(f"[QR] QR Data Length: {len(qr_data)} characters")

                # Determine fill color
                fill_color = 'black'
                try:
                    if record.category_id and record.category_id.category_color:
                        color = (record.category_id.category_color or '').strip()
                        if color:
                            fill_color = color
                            _logger.debug(f"[QR] Using category color: {fill_color}")
                except Exception as e:
                    _logger.warning(f"[QR] Color fallback to black for asset {record.id}: {str(e)}")
                    fill_color = 'black'

                # Generate QR
                try:
                    qr = qrcode.QRCode(
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=4
                    )

                    qr.add_data(qr_data)
                    qr.make(fit=True)

                    img = qr.make_image(fill_color=fill_color, back_color='white')
                    _logger.debug(f"[QR] QR image created successfully for asset {record.id}")

                except Exception as e:
                    _logger.warning(f"[QR] Colored QR failed, fallback default for asset {record.id}: {str(e)}")
                    qr = qrcode.make(qr_data)
                    img = qr

                # Save Image
                try:
                    pil_img = getattr(img, '_img', img)
                    buffer = BytesIO()
                    pil_img.save(buffer, format="PNG")
                    buffer.seek(0)

                    qr_code_data = base64.b64encode(buffer.getvalue()).decode()
                    record.qr_code = qr_code_data

                    _logger.info(
                        f"[QR] QR generated successfully for asset {record.id} "
                        f"(Size: {len(qr_code_data)} bytes)"
                    )

                except Exception as e:
                    _logger.error(f"[QR] Error saving QR for asset {record.id}: {str(e)}")
                    record.qr_code = False

            except Exception as e:
                _logger.error(f"[QR] Unexpected error for asset {record.id}: {str(e)}")
                record.qr_code = False

    def action_regenerate_qr_code(self):
        """Action to manually regenerate QR code for the asset"""
        try:
            self.generate_qr()
            _logger.info(f"QR code regenerated successfully for asset(s): {self.ids}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'QR code regenerated for {len(self)} asset(s)',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error regenerating QR code: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to regenerate QR code: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def get_qr_code_status(self):
        """Get QR code generation status for debugging"""
        status = []
        for record in self:
            status.append({
                'asset_id': record.id,
                'asset_name': record.name,
                'has_qr_code': bool(record.qr_code),
                'qr_code_size': len(record.qr_code) if record.qr_code else 0,
                'has_qr_url': bool(record.qr_url),
                'qr_url': record.qr_url,
            })
        return status

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []

        ctx = self.env.context

        asset_type_id = ctx.get('asset_type_id')
        location_id = ctx.get('location_id')

        if asset_type_id:
            args.append(('asset_name', '=', asset_type_id))

        if location_id:
            args.append(('location_id', '=', location_id))

        if ctx.get('maintenance_asset_pick'):
            # Picking the asset of a new maintenance request: the form's own
            # domain already limits it to Active/Transferable assets, so do not
            # add the role-based status filter (it would exclude every eligible
            # asset for maintenance users).
            _logger.info("name_search → maintenance request asset picker")
        elif self.env.user.has_group(
                'IH_30north_Inventory_assets.group_maintenance_manager'
        ) or self.env.user.has_group(
            'IH_30north_Inventory_assets.group_maintenance_user'
        ):
            args.append(('asset_status', '=', 'under_maintenance'))
            _logger.warning("name_search → Maintenance user")
        else:
            args.append(('asset_status', '=', 'transferable'))
            _logger.warning("name_search → Normal user")

        return super().name_search(name, args, operator=operator, limit=limit)


    # server action for get the color of the qr from category
    # def action_update_assets_qr(self):
    #     """Regenerate QR for all assets in this category."""
    #     assets = self.env['custom.inventory.product'].search([
    #         ('category_id', 'in', self.ids),
    #     ])
    #     assets.generate_qr()
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': 'Done',
    #             'message': f'QR regenerated for {len(assets)} asset(s) in this category.',
    #             'type': 'success',
    #             'sticky': False,
    #         }
    #     }


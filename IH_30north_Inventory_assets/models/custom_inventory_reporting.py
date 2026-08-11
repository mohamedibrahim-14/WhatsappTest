from odoo import models, fields, tools, api
import logging
_logger = logging.getLogger(__name__)


class CustomInventoryReporting(models.Model):
    _name = 'custom.inventory.reporting'
    _description = 'Inventory Reporting'
    _auto = False

    asset_name = fields.Char(string="Asset Name")
    asset_type = fields.Many2one('assets.type', string="Asset Type")
    asset_status = fields.Selection([
        ('active', 'Active'),
        ('transferable', 'Transferable'),
        ('disposed', 'Disposed')
    ], string="Asset Status")
    transfer_date = fields.Date(string="Transfer Date")
    transfer_location = fields.Many2one('custom.inventory.location', string="Location")

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW custom_inventory_reporting AS (
                SELECT
                    row_number() OVER () AS id,
                    p.name AS asset_name,
                    p.asset_name AS asset_type,
                    p.asset_status,
                    m.move_date AS transfer_date,
                    m.location_dest_id AS transfer_location
                FROM
                    custom_inventory_product p
                JOIN
                    custom_inventory_move m ON m.product_id = p.id
                WHERE
                    p.asset_status = 'transferable'
            )
        """)


import html
import logging
from odoo import fields, http
from odoo.http import request
import qrcode
import io

_logger = logging.getLogger(__name__)

# Shared look & feel for every page served after scanning an asset QR code.
PAGE_STYLE = """
    body {
        font-family: 'Roboto', Arial, sans-serif;
        background-color: #f4f6f8;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        margin: 0;
    }
    .card {
        background: white;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        padding: 30px;
        max-width: 450px;
        width: 100%;
        text-align: center;
    }
    h2 { color: #333; margin-bottom: 20px; }
    p { font-size: 16px; color: #555; margin: 10px 0; }
    .btn-odoo {
        background: #0077c0;
        color: white;
        padding: 12px 25px;
        text-decoration: none;
        border: none;
        border-radius: 50px;
        display: inline-block;
        font-weight: 500;
        font-size: 16px;
        cursor: pointer;
        transition: background 0.3s;
    }
    .btn-odoo:hover { background: #005a99; }
    .btn-transfer { background: #28a745; }
    .btn-transfer:hover { background: #1e7e34; }
    hr { border: none; border-top: 1px solid #eee; margin: 20px 0; }
    .field-label { font-weight: 500; color: #333; }
    select, textarea {
        width: 100%;
        padding: 10px;
        margin-top: 5px;
        border: 1px solid #ccc;
        border-radius: 6px;
        font-size: 15px;
        font-family: inherit;
        box-sizing: border-box;
    }
    .form-row { text-align: left; margin: 15px 0; }
    .error { color: #c0392b; font-weight: 500; }
"""


def _render_page(title, body):
    """Wrap `body` in the standard scanned-asset card layout."""
    return f"""
    <html>
        <head>
            <title>{title}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1"/>
            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
            <style>{PAGE_STYLE}</style>
        </head>
        <body>
            <div class="card">{body}</div>
        </body>
    </html>
    """


class AssetQRController(http.Controller):

    @http.route('/asset/info/<int:asset_id>', auth='public', website=True)
    def asset_info(self, asset_id):
        asset = request.env['custom.inventory.product'].sudo().browse(asset_id)
        if not asset.exists():
            return "<h2>Asset Not Found</h2>"

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        odoo_url = f"{base_url}/web#id={asset.id}&model=custom.inventory.product&view_type=form"

        asset_name = html.escape(asset.name or '-')
        serial = html.escape(asset.track_serial or '-')
        asset_type = html.escape(asset.asset_name.name if asset.asset_name else '-')
        location = html.escape(asset.location_id.name if asset.location_id else '-')  # <-- Location
        status = html.escape(
            dict(asset._fields['asset_status'].selection).get(asset.asset_status, '-')
        )

        body = f"""
            <h2>Asset Information</h2>
            <p><span class="field-label">Name:</span> {asset_name}</p>
            <p><span class="field-label">Serial Number:</span> {serial}</p>
            <p><span class="field-label">Asset Type:</span> {asset_type}</p>
            <p><span class="field-label">Asset Location:</span> {location}</p>
            <p><span class="field-label">Status:</span> {status}</p>

            <hr/>

            <p>
                <a href="/asset/transfer/{asset.id}" class="btn-odoo btn-transfer">Transfer Asset</a>
            </p>
            <p>
                <a href="{odoo_url}" class="btn-odoo">Open in Odoo</a>
            </p>
        """
        return _render_page('Asset Information', body)

    # ------------------------------------------------------------------
    # Transfer the scanned asset
    # ------------------------------------------------------------------
    @http.route('/asset/transfer/<int:asset_id>', type='http', auth='user',
                website=True, methods=['GET', 'POST'])
    def asset_transfer(self, asset_id, **post):
        """Move the scanned asset to another location.

        GET  -> pick a destination location.
        POST -> create the draft movement for that destination.

        auth='user' so scanning sends the user through the normal login first;
        creation runs with the user's own rights, never sudo.
        """
        Operation = request.env['custom.inventory.operation']

        if not Operation.check_access_rights('create', raise_exception=False):
            _logger.warning(
                "QR TRANSFER denied | user=%s | no create access on custom.inventory.operation",
                request.env.user.login
            )
            return _render_page('Not Allowed', """
                <h2>Transfer Not Allowed</h2>
                <p class="error">Your user is not allowed to create asset movements.</p>
                <p>Ask an administrator to add you to a group that can move assets.</p>
            """)

        asset = request.env['custom.inventory.product'].sudo().browse(asset_id)
        if not asset.exists():
            return _render_page('Asset Not Found', '<h2>Asset Not Found</h2>')

        asset_name = html.escape(asset.name or '-')
        source = asset.location_id

        # Any active location other than the one the asset already sits in.
        locations = request.env['custom.inventory.location'].search(
            [('active', '=', True), ('id', '!=', source.id)], order='name'
        )

        error = ''
        if request.httprequest.method == 'POST':
            dest = locations.browse(int(post.get('dest_location_id') or 0)).exists()
            if not dest or dest not in locations:
                error = 'Please choose a destination location.'
            else:
                operation = Operation.create({
                    'name': f'QR Transfer - {asset.name or asset.id}',
                    'default_source_location_id': source.id,
                    'default_dest_location_id': dest.id,
                    'date': fields.Date.context_today(request.env.user),
                    'notes': post.get('notes') or '',
                    'move_ids': [(0, 0, {
                        'product_id': asset.id,
                        'asset_type': asset.asset_name.id,
                        'location_id': source.id,
                        'location_dest_id': dest.id,
                    })],
                })

                _logger.info(
                    "QR TRANSFER created | movement=%s(%s) | asset=%s(%s) | %s -> %s | by=%s",
                    operation.sequence_code or operation.name, operation.id,
                    asset.name, asset.id, source.name or '-', dest.name,
                    request.env.user.login
                )

                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                movement_url = (
                    f"{base_url}/web#id={operation.id}"
                    f"&model=custom.inventory.operation&view_type=form"
                )
                return _render_page('Transfer Created', f"""
                    <h2>Transfer Created</h2>
                    <p>Movement <b>{html.escape(operation.sequence_code or operation.name or '')}</b>
                       was created for <b>{asset_name}</b>.</p>
                    <p><span class="field-label">From:</span> {html.escape(source.name or '-')}<br/>
                       <span class="field-label">To:</span> {html.escape(dest.name)}</p>
                    <hr/>
                    <p>It is still in <b>Draft</b> — confirm it in Odoo to apply the move.</p>
                    <p><a href="{movement_url}" class="btn-odoo">Open Movement</a></p>
                    <p><a href="/asset/info/{asset.id}" class="btn-odoo btn-transfer">Back to Asset</a></p>
                """)

        options = ''.join(
            f'<option value="{loc.id}">{html.escape(loc.name or "")}</option>'
            for loc in locations
        )

        return _render_page('Transfer Asset', f"""
            <h2>Transfer Asset</h2>
            <p><span class="field-label">Asset:</span> {asset_name}</p>
            <p><span class="field-label">Current Location:</span>
               {html.escape(source.name or '-')}</p>
            {f'<p class="error">{html.escape(error)}</p>' if error else ''}
            <form method="post" action="/asset/transfer/{asset.id}">
                <input type="hidden" name="csrf_token" value="{request.csrf_token()}"/>
                <div class="form-row">
                    <label class="field-label" for="dest_location_id">Destination Location</label>
                    <select name="dest_location_id" id="dest_location_id" required="required">
                        <option value="">-- Select --</option>
                        {options}
                    </select>
                </div>
                <div class="form-row">
                    <label class="field-label" for="notes">Notes</label>
                    <textarea name="notes" id="notes" rows="2"></textarea>
                </div>
                <hr/>
                <button type="submit" class="btn-odoo btn-transfer">Create Transfer</button>
            </form>
            <p><a href="/asset/info/{asset.id}" class="btn-odoo">Cancel</a></p>
        """)

    @http.route('/asset/qr/print/<int:asset_id>', auth='user')
    def print_qr(self, asset_id):
        asset = request.env['custom.inventory.product'].sudo().browse(asset_id)
        if not asset.exists():
            return "<h2>Asset Not Found</h2>"

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        asset_url = f"{base_url}/asset/info/{asset.id}"

        # Encode the URL only, so scanning opens the asset page directly.
        data = asset_url
        _logger.info("[QR] print_qr | asset=%s(%s) | data=%s", asset.name, asset.id, data)

        # Generate QR
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4
        )

        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save to buffer
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        return request.make_response(
            buf.getvalue(),
            headers=[
                ('Content-Type', 'image/png'),
                ('Content-Disposition', f'inline; filename=asset_{asset.id}_qr.png')
            ]
        )
# -*- coding: utf-8 -*-
from odoo import http, models
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from datetime import date
import re
import logging

_logger = logging.getLogger(__name__)

class CustomWebsiteSale(WebsiteSale):

    # -------------------------------
    # VALIDATION
    # -------------------------------
    def checkout_form_validate(self, mode, all_form_values, data):
        error = {}
        error_message = []

        # 1. Full Name: Arabic, exactly 3 parts
        name = (data.get('name') or '').strip()
        if not name:
            error['name'] = 'missing'
        else:
            name = ' '.join(name.split())
            if not re.fullmatch(r'[\u0600-\u06FF]+( [\u0600-\u06FF]+){2}', name):
                error['name'] = 'error'

        # 2. Email
        email = (data.get('email') or '').strip()
        if not email:
            error['email'] = 'missing'
        elif '@' not in email:
            error['email'] = 'error'

        # 3. Phone (Egyptian mobile)
        phone = (data.get('phone') or '').strip()
        if not phone:
            error['phone'] = 'missing'
        elif not re.fullmatch(r'01[0125]\d{8}', phone):
            error['phone'] = 'error'

        # 4. State/Governorate
        state_id = data.get('state_id')
        if not state_id:
            error['state_id'] = 'missing'
        else:
            try:
                state = request.env['res.country.state'].sudo().browse(int(state_id))
                if not state.exists() or state.country_id.code != 'EG':
                    error['state_id'] = 'error'
            except Exception:
                error['state_id'] = 'error'

        # 5. Date of Birth
        try:
            d = int(data.get('dob_day'))
            m = int(data.get('dob_month'))
            y = int(data.get('dob_year'))
            dob = date(y, m, d)
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                raise ValueError('Underage')
        except Exception:
            error.update({
                'dob_day': 'error',
                'dob_month': 'error',
                'dob_year': 'error',
            })

        # 6. Gender
        gender = (data.get('gender') or '').lower()
        if gender not in ('male', 'female'):
            error['gender'] = 'missing' if not gender else 'error'

        return error, error_message

    # -------------------------------
    # POST PROCESS VALUES
    # -------------------------------
    def values_postprocess(self, order, mode, values, errors, error_msg):
        new = {}
        writable = request.env['ir.model']._get('res.partner')._get_form_writable_fields()

        # Copy only writable fields
        for k, v in values.items():
            if k in writable and v:
                new[k] = v

        egypt = request.env.ref('base.eg')
        new['country_id'] = egypt.id
        new.setdefault('city', 'Cairo')
        new.setdefault('street', 'Egypt')
        new['zip'] = '00000'

        # Governorate
        if values.get('state_id'):
            new['state_id'] = int(values['state_id'])

        # Date of Birth
        if not errors.get('dob_day'):
            try:
                new['date_of_birth'] = date(
                    int(values['dob_year']),
                    int(values['dob_month']),
                    int(values['dob_day'])
                )
            except Exception:
                pass

        # Gender
        if values.get('gender') in ('male', 'female'):
            new['gender'] = values['gender'].capitalize()

        return new, errors, error_msg

    # -------------------------------
    # COUNTRY VALUES
    # -------------------------------
    def _get_country_related_render_values(self, kw, render_values):
        egypt = request.env.ref('base.eg')
        return {
            'country': egypt,
            'countries': egypt,
            'country_states': egypt.state_ids.sorted('name'),
        }

    # -------------------------------
    # ADDRESS PAGE
    # -------------------------------
    @http.route(['/shop/address'], type='http', methods=['GET', 'POST'], auth="public", website=True, sitemap=False)
    def address(self, **kw):
        """Override to add custom fields to checkout context"""
        result = super(CustomWebsiteSale, self).address(**kw)

        # Redirect response
        if isinstance(result, http.Response) and result.status_code in [301, 302, 303]:
            return result

        # Ensure checkout is always a dict
        if hasattr(result, 'qcontext'):
            render_values = result.qcontext
            checkout = render_values.get('checkout')

            # Convert partner record to dict safely
            if checkout:
                if isinstance(checkout, models.Model):
                    partner = checkout
                    checkout = {
                        'name': partner.name or '',
                        'email': partner.email or '',
                        'phone': partner.phone or '',
                        'state_id': partner.state_id.id if partner.state_id else '',
                        'dob_day': partner.date_of_birth.day if getattr(partner, 'date_of_birth', None) else '',
                        'dob_month': partner.date_of_birth.month if getattr(partner, 'date_of_birth', None) else '',
                        'dob_year': partner.date_of_birth.year if getattr(partner, 'date_of_birth', None) else '',
                        'gender': (partner.gender or '').lower(),
                    }
                elif isinstance(checkout, dict):
                    checkout['gender'] = (checkout.get('gender') or '').lower()
            else:
                checkout = {}

            # Preserve posted values
            for field in ['name', 'email', 'phone', 'state_id', 'dob_day', 'dob_month', 'dob_year', 'gender']:
                if kw.get(field):
                    checkout[field] = kw.get(field)

            render_values['checkout'] = checkout

        return result

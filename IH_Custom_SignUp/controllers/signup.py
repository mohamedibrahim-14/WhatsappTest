from odoo import http, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from markupsafe import Markup
import re
from datetime import datetime

class CustomAuthSignupHome(AuthSignupHome):

    def get_auth_signup_qcontext(self):
        qcontext = super(CustomAuthSignupHome, self).get_auth_signup_qcontext()
        countries = request.env['res.country'].sudo().search([('name', '!=', False)], order='name')
        states = request.env['res.country.state'].sudo().search([('country_id', '!=', False)], order='country_id, name')

        qcontext.update({
            'countries': countries,
            'states': states,
            'name': request.params.get('name', ''),
            'mobile': request.params.get('mobile', ''),
            'country_id': request.params.get('country_id', ''),
            'state_id': request.params.get('state_id', ''),
            'dob_day': request.params.get('dob_day', ''),
            'dob_month': request.params.get('dob_month', ''),
            'dob_year': request.params.get('dob_year', ''),
            'gender': request.params.get('gender', ''),
        })
        return qcontext

    def _validate_signup_data(self, values):
        errors = []

        country_id = values.get('country_id')
        country_code = None
        if country_id:
            country = request.env['res.country'].sudo().browse(int(country_id))
            country_code = country.code if country else None

        # ---------------------------
        # Validate name based on country
        # ---------------------------
        name = values.get('name', '').strip()
        if not name:
            errors.append(_('Name is required.'))
        else:
            name = ' '.join(name.split())
            if country_code == 'EG':
                # Arabic validation only for Egypt
                arabic_pattern = re.compile(r'^[\u0600-\u06FF\s]+$')
                if not arabic_pattern.match(name):
                    errors.append(_('Name must contain only Arabic characters.'))
            # For all countries, ensure three parts
            if len(name.split()) != 3:
                errors.append(_('Name must be a triple name (three parts).'))

        # ---------------------------
        # Validate email uniqueness
        # ---------------------------
        email = values.get('login') or values.get('email')
        if not email:
            errors.append(_('Email is required.'))
        elif request.env['res.users'].sudo().search([('login', '=', email)], limit=1):
            errors.append(_('This email address is already registered.'))

        # ---------------------------
        # Validate mobile based on country
        # ---------------------------
        mobile = values.get('mobile', '')
        if not mobile:
            errors.append(_('Mobile number is required.'))
        else:
            mobile_clean = re.sub(r'[\s\-\(\)]', '', mobile)
            if country_code == 'EG':
                if not re.match(r'^01\d{9}$', mobile_clean):
                    errors.append(_('Mobile number must be 11 digits and start with 01 (Egyptian number).'))
            else:
                if len(mobile_clean) < 7 or len(mobile_clean) > 15:
                    errors.append(_('Please enter a valid mobile number.'))

            # Check uniqueness
            if request.env['res.partner'].sudo().search([('mobile', '=', mobile_clean)], limit=1):
                errors.append(_('This mobile number is already registered.'))

            values['mobile'] = mobile_clean

        # ---------------------------
        # Validate country
        # ---------------------------
        if not country_id:
            errors.append(_('Please select a country.'))

        # ---------------------------
        # Validate state
        # ---------------------------
        state_id = values.get('state_id')
        if country_code == 'EG':
            if not state_id:
                errors.append(_('Please select a state for Egypt.'))
            else:
                state = request.env['res.country.state'].sudo().browse(int(state_id))
                if state and country_id and state.country_id.id != int(country_id):
                    errors.append(_('Selected state does not belong to the selected country.'))

        # ---------------------------
        # Validate Date of Birth
        # ---------------------------
        day = values.get('dob_day')
        month = values.get('dob_month')
        year = values.get('dob_year')
        if not all([day, month, year]):
            errors.append(_('Please select complete date of birth.'))
        else:
            try:
                dob_date = datetime(int(year), int(month), int(day)).date()
                if dob_date > datetime.today().date():
                    errors.append(_('Date of birth cannot be in the future.'))
                values['date_of_birth'] = dob_date.strftime('%Y-%m-%d')
            except ValueError:
                errors.append(_('Invalid date of birth.'))

        # ---------------------------
        # Validate gender
        # ---------------------------
        gender = values.get('gender')
        if not gender:
            errors.append(_('Please select a gender.'))

        return errors

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        
        # Only validate if the form was actually submitted (POST request with token)
        if request.httprequest.method == 'POST' and kw.get('token'):
            validation_errors = self._validate_signup_data(kw)
            if validation_errors:
                # Show each error on a separate line using <br>
                qcontext['error'] = Markup('<br/>').join(validation_errors)
                return request.render('auth_signup.signup', qcontext)

        try:
            response = super(CustomAuthSignupHome, self).web_auth_signup(*args, **kw)
            if request.env.uid:
                user = request.env['res.users'].sudo().browse(request.env.uid)
                if user and user.partner_id:
                    user.partner_id.sudo().write({
                        'name': kw.get('name', '').strip(),
                        'mobile': kw.get('mobile'),
                        'country_id': int(kw.get('country_id')) if kw.get('country_id') else False,
                        'state_id': int(kw.get('state_id')) if kw.get('state_id') else False,
                        'date_of_birth': kw.get('date_of_birth'),
                        'gender': kw.get('gender'),
                    })
            return response
        except UserError as e:
            qcontext['error'] = str(e)
            return request.render('auth_signup.signup', qcontext)
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error('Signup error: %s', str(e), exc_info=True)
            qcontext['error'] = _('An error occurred during registration. Please try again.')
            return request.render('auth_signup.signup', qcontext)
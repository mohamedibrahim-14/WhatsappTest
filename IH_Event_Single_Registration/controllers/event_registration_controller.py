from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.addons.website_event_sale.controllers.main import WebsiteEventSaleController


class WebsiteEventRegistrationRouter(WebsiteEventController):
    """
    Routes registration flow depending on event.registration_mode
    """

    @http.route(
        ['/event/<model("event.event"):event>/registration/confirm'],
        type='http', auth='public', methods=['POST'], website=True
    )
    def registration_confirm(self, event, **post):
        """
        Route registration flow depending on event.registration_mode
        ⚠️ CRITICAL: Duplicate check must happen BEFORE calling parent methods
        """
        
        # ========================================
        # STEP 1: DUPLICATE CHECK (BEFORE ANYTHING ELSE)
        # ========================================
        email = post.get('email', '').strip().lower() if post.get('email') else False
        phone = post.get('phone', '').strip() if post.get('phone') else False

        # Check for existing registration BEFORE creating anything
        existing_check = request.env['event.registration'].sudo().search([
            ('event_id', '=', event.id),
            ('state', '!=', 'cancel'),
            '|',
            ('email', '=ilike', email) if email else (0, '=', 1),
            ('phone', '=', phone) if phone else (0, '=', 1)
        ], limit=1)

        if existing_check:
            # User is trying to register again - PREVENT IT
            error_msg = _('You are already registered for this event.')
            if email and existing_check.email and existing_check.email.lower() == email:
                error_msg = _('The email %s is already registered for this event.') % email
            elif phone and existing_check.phone == phone:
                error_msg = _('The phone number %s is already registered for this event.') % phone
            
            request.session['event_registration_error'] = {
                'event_id': event.id,
                'error_title': _('Registration Already Exists'),
                'error_message': error_msg,
            }
            return request.redirect(f'/event/{event.id}/registration/custom-error')

        # ========================================
        # STEP 2: PROCEED WITH REGISTRATION (NO DUPLICATE FOUND)
        # ========================================
        try:
            # 🔹 REGISTER ONLY MODE → no payment required
            if event.registration_mode == 'register_only':
                # Call parent method to create registration
                response = super().registration_confirm(event, **post)
                
                # Check if response is a redirect to success page
                if hasattr(response, 'location') and 'registration/success' in response.location:
                    # Intercept and redirect to our custom success page
                    request.session['event_registration_success'] = {
                        'event_id': event.id,
                        'message': _(
                            'Registration successful! You will receive a confirmation email shortly.'
                        ),
                    }
                    return request.redirect(f'/event/{event.id}/registration/custom-success')
                
                # Return original response if not a success redirect
                return response

            # 🔹 REGISTER & PAY MODE → delegate to sale controller
            return WebsiteEventSaleController().registration_confirm(event, **post)

        except (UserError, ValidationError) as e:
            request.session['event_registration_error'] = {
                'event_id': event.id,
                'error_title': _('Registration Error'),
                'error_message': str(e),
            }
            return request.redirect(f'/event/{event.id}/registration/custom-error')

        except Exception as e:
            request.session['event_registration_error'] = {
                'event_id': event.id,
                'error_title': _('Unexpected Error'),
                'error_message': _(
                    'An unexpected error occurred. Please try again later.'
                ),
            }
            return request.redirect(f'/event/{event.id}/registration/custom-error')

    # ---------------------------------------------------------
    # OVERRIDE PARENT SUCCESS PAGE TO USE OUR CUSTOM ONE
    # ---------------------------------------------------------
    @http.route(
        ['/event/<model("event.event"):event>/registration/success'],
        type='http', auth='public', website=True
    )
    def event_registration_success(self, event, **kwargs):
        """
        Override parent success route to redirect to custom success page
        This prevents the 'missing registration_ids' error
        """
        # Check if we have custom success data
        success_data = request.session.get('event_registration_success')
        
        if success_data and success_data.get('event_id') == event.id:
            # We have custom success data, use our custom page
            return request.redirect(f'/event/{event.id}/registration/custom-success')
        
        # If this is a paid event flow, try to get registration_ids from kwargs or session
        registration_ids = kwargs.get('registration_ids')
        if not registration_ids:
            # Try to find recent registrations for this event
            partner = request.env.user.partner_id if request.env.user._is_public() == False else None
            if partner:
                registrations = request.env['event.registration'].sudo().search([
                    ('event_id', '=', event.id),
                    ('partner_id', '=', partner.id),
                    ('state', '!=', 'cancel')
                ], order='create_date desc', limit=5)
                if registrations:
                    registration_ids = ','.join(str(r.id) for r in registrations)
        
        # If we have registration_ids, call parent method
        if registration_ids:
            return super().event_registration_success(event, registration_ids=registration_ids, **kwargs)
        
        # Fallback to custom success page
        return request.redirect(f'/event/{event.id}/registration/custom-success')

    # ---------------------------------------------------------
    # CUSTOM SUCCESS PAGE
    # ---------------------------------------------------------
    @http.route(
        ['/event/<model("event.event"):event>/registration/custom-success'],
        type='http', auth='public', website=True
    )
    def custom_registration_success(self, event, **kwargs):
        """Custom success page for register-only mode"""
        success_data = request.session.pop('event_registration_success', None)
        
        return request.render(
            'IH_Event_Single_Registration.registration_success_page',
            {
                'event': event,
                'message': success_data.get('message') if success_data else _('Registration successful!'),
                'show_event_link': True,
            }
        )

    # ---------------------------------------------------------
    # CUSTOM ERROR PAGE
    # ---------------------------------------------------------
    @http.route(
        ['/event/<model("event.event"):event>/registration/custom-error'],
        type='http', auth='public', website=True
    )
    def custom_registration_error(self, event, **kwargs):
        """Custom error page for all registration errors"""
        error_data = request.session.pop('event_registration_error', None)
        
        return request.render(
            'IH_Event_Single_Registration.registration_error_page',
            {
                'event': event,
                'error_title': error_data.get('error_title') if error_data else _('Registration Error'),
                'error_message': error_data.get('error_message') if error_data else _('An error occurred.'),
                'show_event_link': True,
            }
        )


class WebsiteEventSaleControllerInherit(WebsiteEventSaleController):
    """
    Inherit sale controller to add duplicate check for paid events
    """

    @http.route(
        ['/event/<model("event.event"):event>/registration/confirm'], 
        type='http', auth="public", methods=['POST'], website=True
    )
    def registration_confirm(self, event, **post):
        """
        Override to add duplicate registration check for paid events
        ⚠️ CRITICAL: Check BEFORE calling parent to prevent registration creation
        """
        
        # Only apply this logic for paid events (register_pay mode)
        if event.registration_mode != 'register_pay':
            # Let the other controller handle register_only mode
            return super(WebsiteEventSaleController, self).registration_confirm(event, **post)
        
        # ========================================
        # DUPLICATE CHECK FOR PAID EVENTS
        # ========================================
        email = post.get('email', '').strip().lower() if post.get('email') else False
        phone = post.get('phone', '').strip() if post.get('phone') else False

        # Search for existing non-cancelled registration
        existing_check = request.env['event.registration'].sudo().search([
            ('event_id', '=', event.id),
            ('state', '!=', 'cancel'),
            '|',
            ('email', '=ilike', email) if email else (0, '=', 1),
            ('phone', '=', phone) if phone else (0, '=', 1)
        ], limit=1)

        if existing_check:
            # Clean up any partially created records first
            self._cleanup_failed_registration()
            
            # Prepare error message
            error_msg = _('You are already registered for this event.')
            if email and existing_check.email and existing_check.email.lower() == email:
                error_msg = _('The email %s is already registered for this event.') % email
            elif phone and existing_check.phone == phone:
                error_msg = _('The phone number %s is already registered for this event.') % phone
            
            request.session['event_registration_error'] = {
                'event_id': event.id,
                'error_title': _('Registration Already Exists'),
                'error_message': error_msg,
            }
            return request.redirect(f'/event/{event.id}/registration/custom-error')

        # ========================================
        # PROCEED WITH PAID REGISTRATION
        # ========================================
        try:
            # Call parent method from WebsiteEventSaleController
            result = super().registration_confirm(event, **post)
            return result
            
        except (UserError, ValidationError) as e:
            self._cleanup_failed_registration()
            request.session['event_registration_error'] = {
                'event_id': event.id,
                'error_title': _('Registration Error'),
                'error_message': str(e),
            }
            return request.redirect(f'/event/{event.id}/registration/custom-error')
            
        except Exception as e:
            self._cleanup_failed_registration()
            request.session['event_registration_error'] = {
                'event_id': event.id,
                'error_title': _('Unexpected Error'),
                'error_message': _('An unexpected error occurred. Please try again later.'),
            }
            return request.redirect(f'/event/{event.id}/registration/custom-error')

    def _cleanup_failed_registration(self):
        """Clean up failed registration attempts"""
        try:
            order_id = request.session.get('sale_order_id')
            if order_id:
                order = request.env['sale.order'].sudo().browse(order_id)
                if order.exists() and order.state in ['draft', 'sent']:
                    # Cancel pending transactions
                    pending_txs = request.env['payment.transaction'].sudo().search([
                        ('sale_order_ids', 'in', order.id),
                        ('state', 'in', ['draft', 'pending', 'authorized'])
                    ])
                    if pending_txs:
                        pending_txs._set_canceled()
                    
                    # Cancel order
                    order.action_cancel()
                    
                    # Cancel registrations
                    registrations = request.env['event.registration'].sudo().search([
                        ('sale_order_id', '=', order.id),
                        ('state', '!=', 'cancel')
                    ])
                    if registrations:
                        registrations.action_cancel()
                    
                    # Delete order
                    order.unlink()
                    
        except Exception as e:
            # Log the error but don't crash
            request.env['ir.logging'].sudo().create({
                'name': 'Event Registration Cleanup',
                'type': 'server',
                'level': 'warning',
                'message': f'Error during cleanup: {str(e)}',
                'path': 'event.registration',
                'func': '_cleanup_failed_registration',
            })
        finally:
            # Clear session data
            keys_to_clear = ['sale_order_id', 'sale_last_order_id', 'website_sale_current_pl']
            for key in keys_to_clear:
                request.session.pop(key, None)
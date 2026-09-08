from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, UserError

class EventRegistration(models.Model):
    _inherit = 'event.registration'

    @api.model
    def check_existing_registration(self, event_id, email=None, phone=None):
        """
        Public method to check if registration exists before creation
        Returns: dict with 'exists' boolean and 'message' if applicable
        """
        if not event_id:
            return {'exists': False}
        
        # Normalize email for comparison
        if email:
            email = email.strip().lower()
        
        if phone:
            phone = phone.strip()
        
        base_domain = [
            ('event_id', '=', event_id),
            ('state', 'in', ['draft', 'open', 'done'])
        ]
        
        # Check email separately
        if email:
            email_domain = base_domain + [('email', '=ilike', email)]
            if self.search(email_domain, limit=1):
                return {
                    'exists': True,
                    'message': _('A registration with this email already exists for this event.')
                }
        
        # Check phone separately
        if phone:
            phone_domain = base_domain + [('phone', '=', phone)]
            if self.search(phone_domain, limit=1):
                return {
                    'exists': True,
                    'message': _('A registration with this phone already exists for this event.')
                }
        
        return {'exists': False}

    def _check_duplicate_registration(self):
        """
        Constraint to prevent duplicate registrations
        This runs AFTER create but BEFORE commit, so it will rollback
        """
        for record in self:
            if record.state in ['draft', 'open', 'done']:
                base_domain = [
                    ('event_id', '=', record.event_id.id),
                    ('state', 'in', ['draft', 'open', 'done']),
                    ('id', '!=', record.id)  # Exclude current record
                ]
                
                # Normalize for comparison
                email = record.email.strip().lower() if record.email else False
                phone = record.phone.strip() if record.phone else False
                
                # Check email separately
                if email:
                    email_domain = base_domain + [('email', '=ilike', email)]
                    if self.search(email_domain, limit=1):
                        raise ValidationError(
                            _('A registration with this email already exists for this event.')
                        )
                
                # Check phone separately
                if phone:
                    phone_domain = base_domain + [('phone', '=', phone)]
                    if self.search(phone_domain, limit=1):
                        raise ValidationError(
                            _('A registration with this phone already exists for this event.')
                        )
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to check for duplicates before creation
        This catches both single and batch creates
        """
        for vals in vals_list:
            # Normalize email and phone
            if vals.get('email'):
                vals['email'] = vals['email'].strip().lower()
            if vals.get('phone'):
                vals['phone'] = vals['phone'].strip()
            
            # Check for duplicates before creation
            check = self.check_existing_registration(
                vals.get('event_id'),
                vals.get('email'),
                vals.get('phone'),
            )
            
            if check.get('exists'):
                # Raise ValidationError to trigger rollback
                raise ValidationError(check.get('message', _('Registration already exists.')))
        
        return super().create(vals_list)


# class SaleOrderLine(models.Model):
#     _inherit = 'sale.order.line'
    
#     def _init_registrations(self):
#         """
#         Override to check for duplicate registrations BEFORE creating them
#         This prevents seat reservation for duplicate registrations
#         """
#         # Get registration values that would be created
#         registrations_vals = []
#         for line in self.filtered(lambda l: l.event_id and l.product_id.detailed_type == 'event'):
#             # Build registration values
#             for count in range(int(line.product_uom_qty)):
#                 registrations_vals.append({
#                     'event_id': line.event_id.id,
#                     'sale_order_id': line.order_id.id,
#                     'sale_order_line_id': line.id,
#                     'partner_id': line.order_id.partner_id.id,
#                     'email': line.order_id.partner_id.email,
#                     'phone': line.order_id.partner_id.phone,
#                 })
        
#         # Check each registration for duplicates BEFORE creating any
#         for vals in registrations_vals:
#             check = self.env['event.registration'].check_existing_registration(
#                 vals.get('event_id'),
#                 vals.get('email'),
#                 vals.get('phone'),
#             )
            
#             if check.get('exists'):
#                 # Cancel the sale order to prevent further processing
#                 self.order_id.action_cancel()
#                 # Raise error to stop the transaction
#                 raise ValidationError(check.get('message', _('Registration already exists.')))
        
#         # If all checks pass, proceed with normal creation
#         return super()._init_registrations()


# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
    
#     def action_confirm(self):
#         """
#         Override to add better error handling for event registrations
#         """
#         # Check for duplicate registrations before confirming
#         for order in self:
#             for line in order.order_line.filtered(lambda l: l.event_id):
#                 check = self.env['event.registration'].check_existing_registration(
#                     line.event_id.id,
#                     order.partner_id.email,
#                     order.partner_id.phone,
#                 )
                
#                 if check.get('exists'):
#                     # Cancel the order
#                     order.action_cancel()
#                     # Raise error
#                     raise ValidationError(check.get('message'))
        
#         return super().action_confirm()
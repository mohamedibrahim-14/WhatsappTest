from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import re

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    # Override name field to add validation
    name = fields.Char(index=True, tracking=True)
    
    gender = fields.Selection([
        ('Male', 'Male'),
        ('Female', 'Female')
    ], string='Gender')

    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    
    @api.depends('date_of_birth')
    def _compute_age(self):
        """Calculate age based on date of birth"""
        today = date.today()
        for partner in self:
            if partner.date_of_birth:
                born = partner.date_of_birth
                partner.age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            else:
                partner.age = 0
    
    # @api.constrains('name')
    # def _check_arabic_triple_name(self):
    #     """Validate that name is a triple Arabic name"""
    #     for partner in self:
    #         # Skip validation for system users and during initial setup
    #         if not partner.name or partner.id <= 2:
    #             continue
            
    #         # Remove extra spaces
    #         name = ' '.join(partner.name.split())
            
    #         # Check if name contains only Arabic characters and spaces
    #         arabic_pattern = re.compile(r'^[\u0600-\u06FF\s]+$')
    #         if not arabic_pattern.match(name):
    #             raise ValidationError(_('Name must contain only Arabic characters.'))
            
    #         # Check if name is a triple name (three parts)
    #         name_parts = name.split()
    #         if len(name_parts) != 3:
    #             raise ValidationError(_('Name must be a triple name (three parts).'))

    # @api.constrains('mobile')
    # def _check_mobile(self):
    #     """Validate mobile number format"""
    #     for partner in self:
    #         if partner.mobile:
    #             # Remove spaces and special characters
    #             mobile = re.sub(r'[\s\-\(\)]', '', partner.mobile)
    #             # Egyptian mobile number validation (starts with +20 or 01, then 10 digits)
    #             if not re.match(r'^(\+20|0020|20)?1[0125]\d{8}$', mobile):
    #                 raise ValidationError(_('Please enter a valid Egyptian mobile number. Format: 01XXXXXXXXX or +201XXXXXXXXX'))
    
    @api.constrains('email')
    def _check_email_format(self):
        """Validate email format"""
        for partner in self:
            if partner.email:
                email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
                if not email_pattern.match(partner.email):
                    raise ValidationError(_('Please enter a valid email address.'))
    
    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        """Validate date of birth"""
        for partner in self:
            if partner.date_of_birth:
                if partner.date_of_birth > date.today():
                    raise ValidationError(_('Date of birth cannot be in the future.'))

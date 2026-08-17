import re

from odoo import models
from odoo.tools import html2plaintext

# Meta refuses a template parameter holding a newline, a tab or four or more
# consecutive spaces, so every run of whitespace is folded into a single space.
WHITESPACE_RUN = re.compile(r"\s+")

# The rendered body of a WhatsApp template may not exceed 1024 characters. A
# description pasted from an email easily runs past that on its own and would
# take the whole send down with it, so it is cut short and the reader is sent
# back to the ticket for the rest.
MAX_VARIABLE_LENGTH = 500


class WhatsappTemplateVariable(models.Model):
    _inherit = "whatsapp.template.variable"

    def _get_field(self):
        """The field this variable reads, following the dotted path, or None."""
        """" author: Mohamed Ebrahem """
        self.ensure_one()
        if self.field_type != "field" or not self.field_name:
            return None

        model = self.env.get(self.model)
        if model is None:
            return None

        field = None
        parts = self.field_name.split(".")
        for index, field_name in enumerate(parts):
            field = model._fields.get(field_name)
            if field is None:
                return None
            if index < len(parts) - 1:
                if not field.comodel_name:
                    return None
                model = self.env[field.comodel_name]
        return field

    def _whatsapp_plaintext(self, value):
        """Flatten an HTML field value into text a WhatsApp parameter accepts."""
        """" author: Mohamed Ebrahem """
        text = WHITESPACE_RUN.sub(" ", html2plaintext(value or "")).strip()
        if len(text) > MAX_VARIABLE_LENGTH:
            text = text[:MAX_VARIABLE_LENGTH].rstrip() + "..."
        return text

    def _get_variables_value(self, record):
        """Render the variables, plain texting the ones reading an Html field.

        A variable pointing at an Html field, such as a ticket description filled
        from an incoming email, is stringified as is by the standard method. The
        markup then reaches the reader verbatim: the recipient gets a wall of
        Outlook '<div style="font-family:Aptos...">' instead of the sentence the
        customer wrote, and the same raw tags are logged in the chatter.
        """
        """" author: Mohamed Ebrahem """
        values = super()._get_variables_value(record)

        for variable in self:
            field = variable._get_field()
            if not field or field.type != "html":
                continue
            key = (
                f"button-{variable.button_id.name}"
                if variable.button_id
                else f"{variable.line_type}-{variable.name}"
            )
            if values.get(key):
                values[key] = variable._whatsapp_plaintext(values[key])

        return values

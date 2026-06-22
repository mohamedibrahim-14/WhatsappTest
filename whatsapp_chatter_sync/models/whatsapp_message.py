from odoo import api, models
from odoo.tools import html_escape


class WhatsappMessage(models.Model):
    _inherit = "whatsapp.message"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for msg in records:
            if msg.message_type == "inbound":

                if msg.res_model and msg.res_id:
                    record = self.env[msg.res_model].browse(msg.res_id)
                    body = html_escape(msg.body or "")

                    record.message_post(
                        body=f"<b>WhatsApp Reply</b><br/>{body}",
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                    )

        return records
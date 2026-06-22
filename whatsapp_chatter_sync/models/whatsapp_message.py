from odoo import models


class WhatsappMessage(models.Model):
    _inherit = "whatsapp.message"

    def create(self, vals_list):
        records = super().create(vals_list)

        for msg in records:
            if msg.message_type == "received":

                if msg.res_model and msg.res_id:
                    record = self.env[msg.res_model].browse(msg.res_id)

                    record.message_post(
                        body=f"<b>WhatsApp Reply</b><br/>{msg.body}",
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                    )

        return records
from odoo import api, models
from odoo.tools import html2plaintext, html_escape
from markupsafe import Markup


class WhatsappMessage(models.Model):
    _inherit = "whatsapp.message"

    def _get_related_record_for_inbound(self):
        """Resolve the business document linked to an inbound WhatsApp message."""
        self.ensure_one()
        mail_message = self.mail_message_id
        if not mail_message or mail_message.model != "discuss.channel" or not mail_message.res_id:
            return self.env["ir.model"]

        channel = self.env["discuss.channel"].browse(mail_message.res_id).exists()
        related_message = channel.whatsapp_mail_message_id
        if not related_message or not related_message.model or not related_message.res_id:
            return self.env["ir.model"]

        return self.env[related_message.model].browse(related_message.res_id).exists()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for msg in records:
            if msg.message_type == "inbound":
                record = msg._get_related_record_for_inbound()
                if record:
                    # Convert incoming HTML payload to text to avoid showing raw tags in chatter.
                    text_body = (html2plaintext(msg.body or "") or "").strip()
                    body = html_escape(text_body).replace("\n", "<br/>")

                    record.message_post(
                        body=Markup(f"<b>WhatsApp Reply</b><br/>{body}"),
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                    )

        return records

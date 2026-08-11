import logging

from odoo import api, models
from odoo.tools import html2plaintext, html_escape
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class WhatsappMessage(models.Model):
    _inherit = "whatsapp.message"

    def _get_source_message_for_inbound(self):
        """Resolve the outbound template message this inbound reply answers."""
        """" author: Mohamed Ebrahem """
        self.ensure_one()
        mail_message = self.mail_message_id
        if not mail_message or mail_message.model != "discuss.channel" or not mail_message.res_id:
            return self.env["mail.message"]

        channel = self.env["discuss.channel"].browse(mail_message.res_id).exists()
        return channel.whatsapp_mail_message_id

    def _get_replied_record(self):
        """The document this reply was made on, as resolved from the webhook.

        whatsapp.account._process_messages puts it in the context, keyed by the
        WhatsApp id of the inbound message. It identifies the exact document the
        technician answered, unlike the channel link which only points at the
        document that opened the conversation.
        """
        """" author: Mohamed Ebrahem """
        self.ensure_one()
        replied_documents = self.env.context.get("ih_wa_replied_documents") or {}
        info = replied_documents.get(self.msg_uid) or {}
        if not info:
            return self.env["ir.model"]
        return self.env[info["model"]].browse(info["res_id"]).exists()

    def _get_related_record_for_inbound(self):
        """Resolve the business document linked to an inbound WhatsApp message."""
        """" author: Mohamed Ebrahem """
        self.ensure_one()
        replied_record = self._get_replied_record()
        if replied_record:
            return replied_record

        related_message = self._get_source_message_for_inbound()
        if not related_message or not related_message.model or not related_message.res_id:
            return self.env["ir.model"]

        return self.env[related_message.model].browse(related_message.res_id).exists()

    @api.model_create_multi
    def create(self, vals_list):
        """" author: Mohamed Ebrahem """
        records = super().create(vals_list)

        for msg in records:
            if msg.message_type != "inbound":
                continue

            record = msg._get_related_record_for_inbound()
            if not record or not hasattr(record, "message_post"):
                continue

            # Convert incoming HTML payload to text to avoid showing raw tags in chatter.
            text_body = (html2plaintext(msg.body or "") or "").strip()
            body = html_escape(text_body).replace("\n", "<br/>")
            record.message_post(
                body=Markup(f"<b>WhatsApp Reply</b><br/>{body}"),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

        return records

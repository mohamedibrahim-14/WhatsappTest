import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)

# A reply counts as a confirmation when its text equals, or contains, one of these
# keywords. Matching is case insensitive, so "Confirm", "confirm" and "CONFIRM"
# all pass, as does a label carrying an emoji such as "Confirm ✅".
CONFIRM_KEYWORDS = ("confirm", "تأكيد")

# Trailing digits compared when matching a sender number against an employee
# mobile: enough to identify a subscriber, short enough to survive the country
# code and the formatting being written differently on each side.
PHONE_MATCH_DIGITS = 9


class WhatsappAccount(models.Model):
    _inherit = "whatsapp.account"

    # ------------------------------------------------------------------
    # reading the webhook payload
    # ------------------------------------------------------------------

    def _get_webhook_messages(self, value):
        """The list of inbound messages carried by a webhook payload."""
        """" author: Mohamed Ebrahem """
        if "messages" not in value and value.get("whatsapp_business_api_data", {}).get("messages"):
            value = value["whatsapp_business_api_data"]
        return value.get("messages", [])

    def _get_reply_text(self, message):
        """The text a reply carries, whatever shape WhatsApp used to send it.

        A tap on a template quick reply button arrives as type 'button' holding the
        button label. A typed answer arrives as type 'text'. Buttons sent outside a
        template arrive as type 'interactive', which Odoo does not process at all,
        so reading the payload here is the only way to see them.
        """
        """" author: Mohamed Ebrahem """
        message_type = message.get("type")
        if message_type == "button":
            return (message.get("button") or {}).get("text") or ""
        if message_type == "text":
            return (message.get("text") or {}).get("body") or ""
        if message_type == "interactive":
            interactive = message.get("interactive") or {}
            reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
            return reply.get("title") or ""
        return ""

    def _is_confirm_reply(self, text):
        """Whether this reply text is a confirmation, case insensitively."""
        """" author: Mohamed Ebrahem """
        normalized = (text or "").strip().casefold()
        if not normalized:
            return False
        return any(keyword in normalized for keyword in CONFIRM_KEYWORDS)

    # ------------------------------------------------------------------
    # finding the ticket a reply belongs to
    # ------------------------------------------------------------------

    def _get_replied_documents(self, messages):
        """Map each reply to the document it was made on.

        A reply carries the id of the message it answers, but Odoo posts the reply
        in a discuss channel and drops that link, because discuss.channel only
        keeps a parent belonging to the same channel. The channel itself points at
        whichever document opened it, so a technician holding several tickets would
        get every reply attributed to a single one. Resolve it here instead, while
        the payload is still available.
        """
        """" author: Mohamed Ebrahem """
        replied_documents = {}
        for message in messages:
            replied_uid = (message.get("context") or {}).get("id")
            if not message.get("id") or not replied_uid:
                continue
            outbound = self.env["whatsapp.message"].sudo().search(
                [("msg_uid", "=", replied_uid)], limit=1
            )
            source = outbound.mail_message_id
            if not source.model or source.model == "discuss.channel" or not source.res_id:
                continue
            replied_documents[message["id"]] = {
                "model": source.model,
                "res_id": source.res_id,
                "template_id": outbound.wa_template_id.id,
            }
            _logger.info(
                "WhatsApp reply %s answers %s#%s (template %s).",
                message["id"], source.model, source.res_id, outbound.wa_template_id.name
            )
        return replied_documents

    def _find_ticket_for_reply(self, message, replied_documents):
        """The helpdesk ticket this reply confirms, empty when undecidable."""
        """" author: Mohamed Ebrahem """
        info = replied_documents.get(message.get("id")) or {}
        if info.get("model") == "helpdesk.ticket":
            ticket = self.env["helpdesk.ticket"].sudo().browse(info["res_id"]).exists()
            if ticket:
                return ticket
        return self._find_ticket_by_number(message.get("from"))

    def _find_ticket_by_number(self, number):
        """Fall back to the sender's number when the answered message is unknown.

        Finds the technician whose mobile ends with the same digits, then their most
        recent ticket that is still waiting for their confirmation.
        """
        """" author: Mohamed Ebrahem """
        Ticket = self.env["helpdesk.ticket"]
        digits = re.sub(r"\D", "", number or "")
        if len(digits) < PHONE_MATCH_DIGITS:
            return Ticket

        suffix = digits[-PHONE_MATCH_DIGITS:]
        employees = self.env["hr.employee"].sudo().search(
            [("mobile_phone", "!=", False)]
        ).filtered(
            lambda emp: re.sub(r"\D", "", emp.mobile_phone).endswith(suffix)
        )
        if not employees:
            _logger.info("WhatsApp confirm: no employee has a mobile ending in %s.", suffix)
            return Ticket

        ticket = Ticket.sudo().search(
            [
                ("employee_helpdesk", "in", employees.ids),
                "|", "|",
                ("stage_id.is_assigned", "=", True),
                ("stage_id.is_submit", "=", True),
                ("stage_id.is_draft", "=", True),
            ],
            order="id desc", limit=1,
        )
        if not ticket:
            _logger.info(
                "WhatsApp confirm: %s has no ticket awaiting confirmation.",
                employees.mapped("name")
            )
        return ticket

    # ------------------------------------------------------------------
    # webhook entry point
    # ------------------------------------------------------------------

    def _process_messages(self, value):
        """" author: Mohamed Ebrahem """
        messages = self._get_webhook_messages(value)
        replied_documents = self._get_replied_documents(messages)

        # The chatter sync in whatsapp.message reads this to post each reply on the
        # document it really answers.
        account = self.with_context(ih_wa_replied_documents=replied_documents)
        result = super(WhatsappAccount, account)._process_messages(value)

        for message in messages:
            text = account._get_reply_text(message)
            if not account._is_confirm_reply(text):
                continue
            ticket = account._find_ticket_for_reply(message, replied_documents)
            if not ticket:
                _logger.info(
                    "WhatsApp confirm %r from %s: no ticket to confirm.",
                    text, message.get("from")
                )
                continue
            _logger.info(
                "WhatsApp confirm %r from %s applies to ticket #%s.",
                text, message.get("from"), ticket.id
            )
            ticket._whatsapp_confirm()

        return result

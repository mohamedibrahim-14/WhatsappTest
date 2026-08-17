from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError

# The WhatsApp template carrying the technician assignment notification. Matched
# case insensitively against both the Odoo name and the name registered with
# Meta, because a template synced back from Meta has its Odoo name rebuilt from
# the remote slug, which title cases it: 'helpdesk1' comes back as 'Helpdesk1'.
WHATSAPP_TEMPLATE_NAME = 'helpdesk1'





class helpdeskproduct(models.Model):
    _inherit = 'helpdesk.ticket'

    # ... existing fields (asset_location_helpdesk, employee_helpdesk, etc.) ...

    # ... existing methods (action_submit, action_checking, etc.) ...

    def _assign_user_from_team(self):
        """Assign user_id based on assignment_team."""
        for rec in self:
            if not rec.assignment_team:
                continue
            user = rec._get_user_for_team(rec.assignment_team)
            if user:
                rec.user_id = user.id

    def _get_whatsapp_free_text_values(self, template):
        """Fill the template's free text body placeholders, in order.

        Only placeholders the template declares as free text are filled: the ones
        typed as 'Field of Model' read the ticket themselves. Values are supplied
        positionally, so a free text placeholder expects the technician name, the
        ticket number and the ticket subject, in that order. Meta rejects a send
        whose placeholders are empty, so a placeholder past the end of that list
        still gets a value. A template built entirely from field variables asks
        for nothing here and gets an empty mapping.
        """
        self.ensure_one()
        values = [
            self.employee_helpdesk.name or '-',
            str(self.id),
            self.name or '-',
        ]
        placeholder_count = len(template.variable_ids.filtered(
            lambda var: var.field_type == 'free_text' and var.line_type == 'body'
        ))
        return {
            f'free_text_{index + 1}': values[index] if index < len(values) else '-'
            for index in range(placeholder_count)
        }

    @api.model
    def _get_whatsapp_assignment_template(self):
        """The approved template used to notify a technician of an assignment."""
        return self.env['whatsapp.template'].search(
            [
                ('status', '=', 'approved'),
                '|',
                ('name', '=ilike', WHATSAPP_TEMPLATE_NAME),
                ('template_name', '=ilike', WHATSAPP_TEMPLATE_NAME),
            ],
            limit=1,
        )

    def _send_whatsapp_assignment_notification(self):
        """Notify the assigned technician via WhatsApp when they're set on the ticket."""
        template = self._get_whatsapp_assignment_template()
        if not template:
            _logger.warning(
                "Approved '%s' WhatsApp template not found.", WHATSAPP_TEMPLATE_NAME
            )
            return
        for rec in self:
            employee = rec.employee_helpdesk
            if not employee or not employee.mobile_phone:
                _logger.warning(
                    "Ticket #%s: technician has no mobile phone set, skipping WhatsApp.",
                    rec.id
                )
                continue
            # No 'active_model' in the context on purpose: it makes the composer's
            # default_get look for a template registered on helpdesk.ticket and
            # raise when there is none. The template is passed explicitly below,
            # and the composer reads its records from res_model / res_ids.
            composer = self.env['whatsapp.composer'].create({
                'res_model': 'helpdesk.ticket',
                'res_ids': str(rec.ids),
                'phone': employee.mobile_phone,
                'wa_template_id': template.id,
                **rec._get_whatsapp_free_text_values(template),
            })
            messages = composer.action_send_whatsapp_template()
            failed = messages.filtered(lambda m: m.state == 'error')
            if failed:
                _logger.error(
                    "Ticket #%s: WhatsApp message to %s failed: %s",
                    rec.id, employee.mobile_phone, failed.mapped('failure_reason')
                )

    def _whatsapp_confirm(self):
        """Run the technician confirmation triggered from WhatsApp.

        Called when the technician taps the 'Confirm' quick reply button on the
        message sent by _send_whatsapp_assignment_notification(). Delegates to
        action_checking() so the WhatsApp path behaves exactly like the Confirm
        button in the form: stage moves to the 'Is Checking' stage and the
        approval activity is filed for the maintenance manager.
        """
        for rec in self:
            stage = rec.stage_id
            # Confirming is only meaningful while the ticket still waits for the
            # technician: once it has reached checking or anything after it, a late
            # reply must not drag the ticket backwards.
            if not (stage.is_draft or stage.is_submit or stage.is_assigned or not stage):
                _logger.info(
                    "Ticket #%s: stage %s is past the technician confirmation, "
                    "ignoring WhatsApp confirmation.",
                    rec.id, stage.name
                )
                continue
            _logger.info(
                "Ticket #%s: WhatsApp confirmation received, moving from stage %s to checking.",
                rec.id, stage.name
            )
            rec.action_checking()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._assign_user_from_team()
        records.filtered(lambda r: r.employee_helpdesk)._send_whatsapp_assignment_notification()
        return records

    def write(self, vals):
        _logger.info("IH_WA write() called on ticket(s) %s with vals keys=%s", self.ids, list(vals.keys()))
        res = super().write(vals)
        if "assignment_team" in vals:
            self._assign_user_from_team()
        if "employee_helpdesk" in vals:
            self.filtered(lambda r: r.employee_helpdesk)._send_whatsapp_assignment_notification()
        return res
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

# Send immediately instead of queueing. Immediate sending blocks the user's
# request for up to SMTP_TIMEOUT (60s, hardcoded in Odoo) per SMTP session
# whenever the mail server is unreachable, so it is off by default.
FORCE_SEND_PARAM = 'ih_30north.mail_force_send'


class IhAssetMailMixin(models.AbstractModel):
    _name = 'ih.asset.mail.mixin'
    _description = 'Asset Workflow Email Notifications'

    @api.model
    def _mail_force_send(self):
        """True when mails must be pushed out inside the current request."""
        return self.env['ir.config_parameter'].sudo().get_param(
            FORCE_SEND_PARAM, 'False'
        ).strip().lower() in ('1', 'true', 'yes')

    def _send_email_to_users(self, users, subject, body_html):
        """Notify every active user in `users` about this record.

        Mails are created in one batch and, by default, left for the
        "Mail: Email Queue Manager" cron to deliver, so the workflow button
        returns immediately even when SMTP is slow or down. Set the
        `ih_30north.mail_force_send` system parameter to True to deliver
        inside the request instead (one SMTP session for the whole batch).

        Never raises: every skip and every failure is logged with its reason.
        """
        self.ensure_one()
        _logger.info(
            "MAIL start | %s(%s) | subject=%r | candidates=%s",
            self._name, self.id, subject, users.mapped('login') or []
        )

        if not users:
            _logger.warning(
                "MAIL not sent | %s(%s) | subject=%r | reason=no users given "
                "(the security group has no members?)",
                self._name, self.id, subject
            )
            return

        if not self.env['ir.mail_server'].sudo().search_count([]):
            _logger.error(
                "MAIL blocked | no outgoing mail server configured "
                "(Settings > Technical > Email > Outgoing Mail Servers). "
                "Mails will stay queued."
            )

        vals_list, recipients, skipped = [], [], []

        for user in users:
            if not user.active:
                skipped.append((user.login, 'user archived'))
                continue

            email_to = user.partner_id.email or user.email
            if not email_to:
                skipped.append((user.login, 'no email address on user/partner'))
                continue

            recipients.append((user.login, email_to))
            vals_list.append({
                'subject': subject,
                'body_html': body_html,
                'email_to': email_to,
                # Keep the record so failures stay visible in
                # Settings > Technical > Email > Emails.
                'auto_delete': False,
                'model': self._name,
                'res_id': self.id,
            })

        if skipped:
            _logger.warning(
                "MAIL skipped recipients | %s(%s) | %s", self._name, self.id, skipped
            )

        if not vals_list:
            _logger.warning(
                "MAIL not sent | %s(%s) | subject=%r | reason=no usable recipient address",
                self._name, self.id, subject
            )
            return {'sent': [], 'queued': [], 'skipped': skipped, 'failed': []}

        try:
            mails = self.env['mail.mail'].sudo().create(vals_list)
        except Exception:
            _logger.exception(
                "MAIL create failed | %s(%s) | recipients=%s",
                self._name, self.id, recipients
            )
            return {
                'sent': [], 'queued': [], 'skipped': skipped,
                'failed': [(login, email, 'mail.mail create failed') for login, email in recipients],
            }

        force_send = self._mail_force_send()
        if force_send:
            try:
                # One send() for the whole batch = one SMTP session, instead of
                # reconnecting (and re-waiting the timeout) per recipient.
                mails.send(raise_exception=False)
            except Exception:
                _logger.exception(
                    "MAIL send raised | %s(%s) | mail_ids=%s", self._name, self.id, mails.ids
                )
        else:
            _logger.info(
                "MAIL queued | %s(%s) | mail_ids=%s | delivery left to the "
                "'Mail: Email Queue Manager' cron (set %s=True to send immediately)",
                self._name, self.id, mails.ids, FORCE_SEND_PARAM
            )

        sent, queued, failed = [], [], []
        for mail, (login, email_to) in zip(mails, recipients):
            mail = mail.sudo().exists()
            if not mail:
                # auto_delete removed it -> it went out fine.
                sent.append((login, email_to))
            elif mail.state == 'sent':
                sent.append((login, email_to))
            elif mail.state == 'exception':
                reason = mail.failure_reason or 'unknown SMTP error'
                failed.append((login, email_to, reason))
                _logger.error(
                    "MAIL FAILED | %s(%s) | mail_id=%s to=%s | type=%s | reason=%s",
                    self._name, self.id, mail.id, email_to,
                    mail.failure_type or 'n/a', reason
                )
            else:
                queued.append((login, email_to, mail.state))

        _logger.info(
            "MAIL summary | %s(%s) | subject=%r | force_send=%s | "
            "sent=%s queued=%s skipped=%s failed=%s",
            self._name, self.id, subject, force_send, sent, queued, skipped, failed
        )
        return {'sent': sent, 'queued': queued, 'skipped': skipped, 'failed': failed}

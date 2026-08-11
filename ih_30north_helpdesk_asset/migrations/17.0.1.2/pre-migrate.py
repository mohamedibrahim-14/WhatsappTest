import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Drop the leftover Selection values of the old ``assignment_team`` field.

    When the field was a Selection, the ORM stored one ir.model.fields.selection
    row per value ('it', 'maintenance') plus its ir.model.data entry. Now that
    the field is a Many2one, ir.model.data._process_end() tries to unlink those
    orphan rows and calls _process_ondelete(), which does
    ``(field.ondelete or {}).get(value)``. A Many2one's ``ondelete`` is the
    string 'set null', not a dict, so that raises:

        AttributeError: 'str' object has no attribute 'get'

    Removing the rows here, before the registry reaches _process_end, avoids it.
    """
    if not version:
        return

    cr.execute("""
        SELECT id
          FROM ir_model_fields
         WHERE model = 'helpdesk.ticket'
           AND name = 'assignment_team'
    """)
    field_ids = [row[0] for row in cr.fetchall()]
    if not field_ids:
        return

    cr.execute("""
        SELECT id
          FROM ir_model_fields_selection
         WHERE field_id IN %s
    """, (tuple(field_ids),))
    selection_ids = [row[0] for row in cr.fetchall()]
    if not selection_ids:
        return

    # The ir.model.data entries first, otherwise _process_end still finds them
    # dangling and tries to unlink records that no longer exist.
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE model = 'ir.model.fields.selection'
           AND res_id IN %s
    """, (tuple(selection_ids),))

    cr.execute("""
        DELETE FROM ir_model_fields_selection
         WHERE id IN %s
    """, (tuple(selection_ids),))

    _logger.info(
        "Removed %d obsolete selection value(s) of helpdesk.ticket.assignment_team.",
        len(selection_ids),
    )

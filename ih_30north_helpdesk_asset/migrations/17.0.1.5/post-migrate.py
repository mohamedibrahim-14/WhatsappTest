import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _drop_orphan_menus(cr):
    """Remove the duplicate Assignment Teams menu left over by 17.0.1.4.

    That migration deleted the ir_model_data rows for the assignment team menu
    and action but not the records themselves, so they survived without an
    xmlid. Reloading this module's XML then created a second set, leaving two
    identical "Assignment Teams" entries under Configuration. Anything pointing
    at helpdesk.assignment.team with no ir_model_data row is one of those
    orphans — the records the XML owns always have one.
    """
    cr.execute("""
        DELETE FROM ir_ui_menu m
         WHERE m.action IN (
                   SELECT 'ir.actions.act_window,' || a.id
                     FROM ir_act_window a
                    WHERE a.res_model = 'helpdesk.assignment.team'
               )
           AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data d
                    WHERE d.model = 'ir.ui.menu' AND d.res_id = m.id
               )
    """)
    if cr.rowcount:
        _logger.info("Removed %d orphaned Assignment Teams menu(s).", cr.rowcount)

    cr.execute("""
        DELETE FROM ir_act_window a
         WHERE a.res_model = 'helpdesk.assignment.team'
           AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data d
                    WHERE d.model = 'ir.actions.act_window' AND d.res_id = a.id
               )
    """)
    if cr.rowcount:
        _logger.info("Removed %d orphaned Assignment Teams action(s).", cr.rowcount)


def migrate(cr, version):
    """Restore the assignment teams that 17.0.1.4 removed.

    17.0.1.4 consolidated everything onto helpdesk.team and dropped
    helpdesk.assignment.team. That consolidation is reverted: assignment teams
    are back and hold the technicians, while helpdesk.team only carries
    warehouse_user_ids.

    17.0.1.4 had copied each assignment team's employees into
    helpdesk_team_technician_rel before dropping the table. That relation is the
    only surviving trace of the old membership, so it is replayed here into
    freshly created assignment teams named after the helpdesk team they came
    from. The table is then dropped.
    """
    if not version:
        return

    _drop_orphan_menus(cr)

    cr.execute("SELECT to_regclass('helpdesk_team_technician_rel')")
    if not cr.fetchone()[0]:
        return

    cr.execute("""
        SELECT rel.team_id, array_agg(rel.employee_id)
          FROM helpdesk_team_technician_rel rel
      GROUP BY rel.team_id
    """)
    recovered = cr.fetchall()
    if recovered:
        env = api.Environment(cr, SUPERUSER_ID, {})
        Team = env['helpdesk.assignment.team']
        for helpdesk_team_id, employee_ids in recovered:
            helpdesk_team = env['helpdesk.team'].browse(helpdesk_team_id).exists()
            name = helpdesk_team.display_name if helpdesk_team else 'Recovered Team'
            if Team.search_count([('name', '=', name)]):
                continue
            Team.create({'name': name, 'employee_ids': [(6, 0, employee_ids)]})
            _logger.info(
                "Recreated assignment team '%s' with %d employee(s).",
                name, len(employee_ids),
            )

    cr.execute("DROP TABLE IF EXISTS helpdesk_team_technician_rel")

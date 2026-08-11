import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Consolidate on helpdesk.team and retire helpdesk.assignment.team.

    Technicians and warehouse approvers now live on the native helpdesk.team,
    selected through the ticket's team_id. The separate assignment team model
    and the ticket's assignment_team field are dropped.

    The old technician links are carried over: every employee listed on an
    assignment team is copied onto each helpdesk team whose tickets used that
    assignment team, so no Technician configuration is lost.
    """
    if not version:
        return

    def table_exists(name):
        cr.execute("SELECT to_regclass(%s)", (name,))
        return cr.fetchone()[0] is not None

    def column_exists(table, column):
        cr.execute("""
            SELECT 1 FROM information_schema.columns
             WHERE table_name = %s AND column_name = %s
        """, (table, column))
        return bool(cr.fetchone())

    # ---- carry technicians over to the helpdesk teams that were using them ----
    if (
        table_exists('helpdesk_assignment_team_employee_rel')
        and column_exists('helpdesk_ticket', 'assignment_team')
    ):
        cr.execute("""
            CREATE TABLE IF NOT EXISTS helpdesk_team_technician_rel (
                team_id integer NOT NULL REFERENCES helpdesk_team(id) ON DELETE CASCADE,
                employee_id integer NOT NULL REFERENCES hr_employee(id) ON DELETE CASCADE,
                PRIMARY KEY (team_id, employee_id)
            )
        """)
        cr.execute("""
            INSERT INTO helpdesk_team_technician_rel (team_id, employee_id)
            SELECT DISTINCT t.team_id, rel.employee_id
              FROM helpdesk_ticket t
              JOIN helpdesk_assignment_team_employee_rel rel
                ON rel.team_id = t.assignment_team
             WHERE t.team_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """)
        if cr.rowcount:
            _logger.info("Copied %d technician link(s) onto helpdesk teams.", cr.rowcount)

    # ---- drop the ticket field ----
    if column_exists('helpdesk_ticket', 'assignment_team'):
        cr.execute("ALTER TABLE helpdesk_ticket DROP COLUMN assignment_team")

    # The pre-1.1 Selection values were parked here; nothing reads them now.
    if column_exists('helpdesk_ticket', 'assignment_team_legacy'):
        cr.execute("ALTER TABLE helpdesk_ticket DROP COLUMN assignment_team_legacy")

    # ---- drop the model itself ----
    cr.execute("DROP TABLE IF EXISTS helpdesk_assignment_team_employee_rel")
    cr.execute("DROP TABLE IF EXISTS helpdesk_assignment_team CASCADE")

    # Clear the metadata by hand. Left behind, ir.model.data._process_end tries
    # to unlink these itself and can fail the whole registry load.
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE module = 'ih_30north_helpdesk_asset'
           AND (name LIKE '%%assignment_team%%' OR name LIKE '%%assignment.team%%')
    """)
    cr.execute("""
        DELETE FROM ir_model_fields
         WHERE model = 'helpdesk.assignment.team'
            OR (model = 'helpdesk.ticket'
                AND name IN ('assignment_team', 'is_helpdesk_team_member'))
    """)
    cr.execute("DELETE FROM ir_model WHERE model = 'helpdesk.assignment.team'")
    _logger.info("helpdesk.assignment.team removed; cycle now driven by team_id.")

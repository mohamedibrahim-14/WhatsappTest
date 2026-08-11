import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Move the old Selection column out of the way.

    ``assignment_team`` changed from Selection (varchar holding 'it' /
    'maintenance') to Many2one on helpdesk.assignment.team (int4). Postgres
    cannot cast 'it' to an integer, so the ORM's automatic conversion raises
    InvalidTextRepresentation. Renaming the column lets the ORM create a fresh
    int4 one, while keeping the old values readable for remapping.
    """
    if not version:
        return

    cr.execute("""
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'helpdesk_ticket'
           AND column_name = 'assignment_team'
    """)
    row = cr.fetchone()
    if not row:
        return

    # Already an int4 column: a previous run converted it, nothing to do.
    if row[0] not in ('character varying', 'text'):
        return

    cr.execute("""
        ALTER TABLE helpdesk_ticket
        RENAME COLUMN assignment_team TO assignment_team_legacy
    """)
    _logger.info(
        "helpdesk_ticket.assignment_team renamed to assignment_team_legacy; "
        "old Selection values preserved there for remapping."
    )

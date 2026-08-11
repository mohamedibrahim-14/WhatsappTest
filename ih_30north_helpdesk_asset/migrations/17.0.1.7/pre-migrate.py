import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Merge the two warehouse stages into one.

    The cycle used to be: Waiting for Warehouse Availability (Check Availability)
    -> Warehouse Confirm Availability (Spare Parts Available). Warehouse now
    confirms straight from the waiting stage, so ``is_warehouse_availability``
    is dropped and only ``is_waiting_warehouse_availability`` remains.

    Tickets parked in the removed stage are moved to the surviving one — left
    behind they would sit in a stage carrying no flag at all, which the ticket
    reads as Draft.
    """
    if not version:
        return

    def column_exists(column):
        cr.execute("""
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'helpdesk_stage' AND column_name = %s
        """, (column,))
        return bool(cr.fetchone())

    if not column_exists('is_warehouse_availability'):
        return

    if not column_exists('is_waiting_warehouse_availability'):
        cr.execute("""
            ALTER TABLE helpdesk_stage
            ADD COLUMN is_waiting_warehouse_availability boolean
        """)

    # No waiting stage configured? Promote the confirm stage into that role so
    # the cycle still has a target for action_maintenance_approve.
    cr.execute("SELECT id FROM helpdesk_stage WHERE is_waiting_warehouse_availability IS TRUE")
    waiting_ids = [row[0] for row in cr.fetchall()]
    if not waiting_ids:
        cr.execute("""
            UPDATE helpdesk_stage
               SET is_waiting_warehouse_availability = true
             WHERE is_warehouse_availability IS TRUE
         RETURNING id
        """)
        waiting_ids = [row[0] for row in cr.fetchall()]
        if waiting_ids:
            _logger.info(
                "Promoted %d stage(s) to is_waiting_warehouse_availability.",
                len(waiting_ids),
            )

    # Move tickets out of the stage that is losing its flag.
    if waiting_ids:
        cr.execute("""
            UPDATE helpdesk_ticket t
               SET stage_id = %s
             WHERE t.stage_id IN (
                       SELECT id FROM helpdesk_stage
                        WHERE is_warehouse_availability IS TRUE
                          AND is_waiting_warehouse_availability IS NOT TRUE
                   )
        """, (waiting_ids[0],))
        if cr.rowcount:
            _logger.info(
                "Moved %d ticket(s) from the removed warehouse confirm stage.",
                cr.rowcount,
            )

    cr.execute("ALTER TABLE helpdesk_stage DROP COLUMN is_warehouse_availability")
    cr.execute("""
        DELETE FROM ir_model_fields
         WHERE model = 'helpdesk.stage' AND name = 'is_warehouse_availability'
    """)
    _logger.info("Dropped helpdesk_stage.is_warehouse_availability.")

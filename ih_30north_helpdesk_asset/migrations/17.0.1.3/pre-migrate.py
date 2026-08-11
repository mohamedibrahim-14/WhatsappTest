import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Retire the finance stage flags and rename the warehouse one.

    The spare-parts branch no longer goes through Finance: Warehouse confirms
    availability instead. ``is_waiting_finance`` / ``is_finance`` are dropped,
    and any stage that carried one of them is switched to the new
    ``is_warehouse_availability`` flag so the cycle keeps working.
    """
    if not version:
        return

    def has_column(name):
        cr.execute("""
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'helpdesk_stage' AND column_name = %s
        """, (name,))
        return bool(cr.fetchone())

    # An earlier revision of this change shipped the flag as is_waiting_warehouse.
    if has_column('is_waiting_warehouse') and not has_column('is_warehouse_availability'):
        cr.execute("""
            ALTER TABLE helpdesk_stage
            RENAME COLUMN is_waiting_warehouse TO is_warehouse_availability
        """)
        _logger.info("Renamed helpdesk_stage.is_waiting_warehouse to is_warehouse_availability.")

    if not has_column('is_warehouse_availability'):
        cr.execute("ALTER TABLE helpdesk_stage ADD COLUMN is_warehouse_availability boolean")

    # Carry the old finance stages over to the new flag rather than silently
    # leaving the cycle with no availability-check stage at all.
    for old_column in ('is_waiting_finance', 'is_finance'):
        if not has_column(old_column):
            continue
        cr.execute("""
            UPDATE helpdesk_stage
               SET is_warehouse_availability = true
             WHERE %s IS TRUE
               AND is_warehouse_availability IS NOT TRUE
        """ % old_column)
        if cr.rowcount:
            _logger.info(
                "Moved %d stage(s) from %s to is_warehouse_availability.",
                cr.rowcount, old_column,
            )
        cr.execute("ALTER TABLE helpdesk_stage DROP COLUMN %s" % old_column)

    # The separate "Warehouse Received" stage is gone: Warehouse confirming
    # availability now moves the ticket straight to the SP Installed stage.
    if has_column('is_warehouse_received'):
        cr.execute("ALTER TABLE helpdesk_stage DROP COLUMN is_warehouse_received")

    cr.execute("""
        DELETE FROM ir_model_fields
         WHERE model = 'helpdesk.stage'
           AND name IN ('is_waiting_finance', 'is_finance',
                        'is_waiting_warehouse', 'is_warehouse_received')
    """)

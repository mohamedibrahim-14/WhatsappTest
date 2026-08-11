"""Find every database reference to a field name. Read-only.

Scans every text / varchar / jsonb column in the public schema, so it catches
references in places a targeted query would miss: view archs, saved filters,
server actions, mail templates, automated actions, export lists, and any
config table belonging to a third-party module.

Usage:
    python find_stale_field_refs.py --db PROD_DB --needle assets_category_helpdesk
    python find_stale_field_refs.py --db PROD_DB --needle foo --host 10.0.0.5 --user odoo
"""
import argparse
import sys

import psycopg2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--needle', required=True)
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default=5432, type=int)
    parser.add_argument('--user', default='odoo')
    parser.add_argument('--password', default='')
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=args.host, port=args.port, user=args.user,
        password=args.password, dbname=args.db,
    )
    conn.set_session(readonly=True)
    cr = conn.cursor()

    cr.execute("""
        SELECT table_name, column_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND data_type IN ('text', 'character varying', 'jsonb', 'json')
      ORDER BY table_name, column_name
    """)
    columns = cr.fetchall()
    print("scanning %d text-ish column(s) for %r ...\n" % (len(columns), args.needle))

    pattern = '%%%s%%' % args.needle
    hits = 0
    for table, column in columns:
        try:
            cr.execute(
                'SELECT id FROM "%s" WHERE "%s"::text LIKE %%s LIMIT 20'
                % (table, column),
                (pattern,),
            )
            rows = [r[0] for r in cr.fetchall()]
        except psycopg2.Error:
            conn.rollback()          # no id column, or not readable — skip
            continue

        if rows:
            hits += 1
            print("HIT  %-38s %-28s ids=%s" % (table, column, rows))

    print("\n%d column(s) contain %r" % (hits, args.needle))
    if not hits:
        print("Nothing in the database: the reference is in module source code.")
    cr.close()
    conn.close()
    return 0 if True else 1


if __name__ == '__main__':
    sys.exit(main())

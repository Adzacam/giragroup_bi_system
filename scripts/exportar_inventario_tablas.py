import psycopg2

URL_SNAPSHOT = 'postgresql://giragroup_user:giragroup_secret_2026@localhost:5434/snapshot_dw_20261110_1201'
conn = psycopg2.connect(URL_SNAPSHOT)
cur = conn.cursor()
cur.execute('''
    SELECT table_schema, table_name, table_type 
    FROM information_schema.tables 
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_schema, table_name;
''')
tables = cur.fetchall()
print(f'Total tablas/vistas DW: {len(tables)}')
for s, t, ty in tables:
    cur.execute(f'SELECT count(*) FROM "{s}"."{t}"')
    cnt = cur.fetchone()[0]
    print(f'{s}.{t} ({ty}): {cnt}')

URL_CATALOG = 'postgresql://giragroup_user:giragroup_secret_2026@localhost:5433/giragroup_catalog_db'
conn_c = psycopg2.connect(URL_CATALOG)
cur_c = conn_c.cursor()
cur_c.execute('''
    SELECT table_schema, table_name, table_type 
    FROM information_schema.tables 
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_schema, table_name;
''')
cat_tables = cur_c.fetchall()
print(f'Total tablas Catalog DB: {len(cat_tables)}')
for s, t, ty in cat_tables:
    cur_c.execute(f'SELECT count(*) FROM "{s}"."{t}"')
    cnt = cur_c.fetchone()[0]
    print(f'{s}.{t} ({ty}): {cnt}')

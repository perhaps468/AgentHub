# -*- coding: utf-8 -*-
import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='710802',
    database='agenthub',
    charset='utf8mb4'
)

with open('sql/007_p6_orchestration_runs_and_tasks.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

cursor = conn.cursor()
for statement in sql_content.split(';'):
    stmt = statement.strip()
    if stmt:
        try:
            cursor.execute(stmt)
            print(f'OK: {stmt[:80]}')
        except Exception as e:
            print(f'ERROR: {e}')

conn.commit()
cursor.close()
conn.close()
print('Done!')

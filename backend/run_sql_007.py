# -*- coding: utf-8 -*-
import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='710802',
    charset='utf8mb4',
    multi_statements=True,
)

with open('sql/agenthub.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

cursor = conn.cursor()
try:
    for _ in cursor.execute(sql_content, multi=True):
        pass
    conn.commit()
    print('Executed sql/agenthub.sql')
finally:
    cursor.close()
    conn.close()

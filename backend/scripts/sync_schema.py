import pymysql

conn = pymysql.connect(
    host='127.0.0.1', port=3306,
    user='root', password='710802', database='agenthub'
)
cursor = conn.cursor()

# Add updated_at column to sessions
try:
    cursor.execute("""
        ALTER TABLE sessions
        ADD COLUMN updated_at datetime NOT NULL
        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        AFTER created_at
    """)
    conn.commit()
    print("updated_at column added to sessions")
except pymysql.err.OperationalError as e:
    if 'Duplicate' in str(e) or 'Already exists' in str(e):
        print("updated_at column already exists in sessions")
    else:
        raise

cursor.close()
conn.close()
print("Done.")

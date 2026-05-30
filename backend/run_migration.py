import pymysql

# Database connection config
DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = '710802'
DB_NAME = 'agenthub'

def run_migration():
    # First connect without database to create it
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )

    try:
        with conn.cursor() as cursor:
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"Database '{DB_NAME}' created or already exists")

            # Use the database
            cursor.execute(f"USE `{DB_NAME}`")

            # Check if users table exists
            cursor.execute("SHOW TABLES LIKE 'users'")
            users_exists = cursor.fetchone()

            if not users_exists:
                print("Creating users table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                     id              BIGINT UNSIGNED   PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
                     username        VARCHAR(50)       NOT NULL UNIQUE COMMENT '登录用户名，同时也是显示名称',
                     password        VARCHAR(255)      NOT NULL COMMENT '登录密码（明文）',
                     avatar          VARCHAR(500)      DEFAULT NULL COMMENT '头像URL',
                     created_at      DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表'
                """)
                print("users table created")

                # Insert test users
                print("Inserting test users...")
                cursor.execute("INSERT INTO users (username, password) VALUES ('gy', 'admin123'), ('ljw', 'admin123')")
                print("Test users inserted")

            # Check if sessions table exists
            cursor.execute("SHOW TABLES LIKE 'sessions'")
            sessions_exists = cursor.fetchone()

            if not sessions_exists:
                print("Creating sessions table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                      id CHAR(36) PRIMARY KEY,
                      owner_id VARCHAR(100) NOT NULL,
                      workspace_id CHAR(36) DEFAULT NULL,
                      title VARCHAR(255),
                      mode VARCHAR(20) NOT NULL DEFAULT 'single',
                      is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
                      is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      INDEX idx_sessions_owner_updated (owner_id, updated_at),
                      INDEX idx_sessions_archived (owner_id, is_archived),
                      INDEX idx_sessions_workspace (workspace_id),
                      CONSTRAINT chk_sessions_mode CHECK (mode IN ('single', 'group'))
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                print("sessions table created")

            # Check if messages table exists
            cursor.execute("SHOW TABLES LIKE 'messages'")
            messages_exists = cursor.fetchone()

            if not messages_exists:
                print("Creating messages table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                      id CHAR(36) NOT NULL,
                      session_id CHAR(36) NOT NULL,
                      sender_type VARCHAR(20) NOT NULL,
                      sender_role VARCHAR(50) DEFAULT NULL,
                      content TEXT NOT NULL,
                      type VARCHAR(20) NOT NULL DEFAULT 'text',
                      status VARCHAR(20) NOT NULL DEFAULT 'completed',
                      payload JSON NOT NULL DEFAULT ('{}'),
                      msg_metadata JSON NOT NULL DEFAULT ('{}'),
                      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      INDEX idx_messages_session_created (session_id, created_at),
                      CONSTRAINT chk_messages_sender_type CHECK (sender_type IN ('human', 'agent', 'system')),
                      CONSTRAINT chk_messages_type CHECK (type IN ('text', 'code', 'diff', 'artifact', 'deploy')),
                      CONSTRAINT chk_messages_status CHECK (status IN ('pending', 'streaming', 'completed', 'failed')),
                      CONSTRAINT fk_messages_session
                        FOREIGN KEY (session_id)
                        REFERENCES sessions(id)
                        ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                print("messages table created")

            # Check if workspaces table exists
            cursor.execute("SHOW TABLES LIKE 'workspaces'")
            workspaces_exists = cursor.fetchone()

            if not workspaces_exists:
                print("Creating workspaces table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS workspaces (
                      id CHAR(36) PRIMARY KEY,
                      owner_id VARCHAR(100) NOT NULL,
                      root_path VARCHAR(512) NOT NULL,
                      name VARCHAR(255) NOT NULL,
                      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      INDEX idx_workspaces_owner (owner_id),
                      INDEX idx_workspaces_root (owner_id, root_path(255))
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                print("workspaces table created")

            # ===== Add missing columns to messages table =====
            cursor.execute("DESCRIBE messages")
            columns = {row[0] for row in cursor.fetchall()}

            if 'status' not in columns:
                print("Adding 'status' column to messages...")
                cursor.execute("ALTER TABLE messages ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'completed'")
                print("'status' column added")

            if 'type' not in columns:
                print("Adding 'type' column to messages...")
                cursor.execute("ALTER TABLE messages ADD COLUMN type VARCHAR(20) NOT NULL DEFAULT 'text'")
                print("'type' column added")

            if 'payload' not in columns:
                print("Adding 'payload' column to messages...")
                cursor.execute("ALTER TABLE messages ADD COLUMN payload JSON NOT NULL DEFAULT ('{}')")
                print("'payload' column added")

            if 'msg_metadata' not in columns:
                print("Adding 'msg_metadata' column to messages...")
                cursor.execute("ALTER TABLE messages ADD COLUMN msg_metadata JSON NOT NULL DEFAULT ('{}')")
                print("'msg_metadata' column added")

            # ===== Add missing columns to sessions table =====
            cursor.execute("DESCRIBE sessions")
            session_columns = {row[0] for row in cursor.fetchall()}

            if 'workspace_id' not in session_columns:
                print("Adding 'workspace_id' column to sessions...")
                cursor.execute("ALTER TABLE sessions ADD COLUMN workspace_id CHAR(36) DEFAULT NULL")
                cursor.execute("ALTER TABLE sessions ADD INDEX idx_sessions_workspace (workspace_id)")
                print("'workspace_id' column added")

            # ===== Add missing columns to workspaces table =====
            cursor.execute("DESCRIBE workspaces")
            ws_columns = {row[0] for row in cursor.fetchall()}

            if 'name' not in ws_columns:
                print("Adding 'name' column to workspaces...")
                cursor.execute("ALTER TABLE workspaces ADD COLUMN name VARCHAR(255) NOT NULL")
                print("'name' column added")

        conn.commit()
        print("\nMigration completed successfully!")

        # Show final table structure
        with conn.cursor() as cursor:
            cursor.execute("USE `agenthub`")
            cursor.execute("SHOW TABLES")
            print("\nTables in database:")
            for row in cursor.fetchall():
                print(f"  - {row[0]}")

    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()

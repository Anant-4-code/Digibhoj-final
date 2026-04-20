import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "digibhoj.db")

def migrate():
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if subscription_id already exists to avoid errors on multiple runs
        cursor.execute("PRAGMA table_info(payments)")
        columns = [col[1] for col in cursor.fetchall()]
        if "subscription_id" in columns:
            print("Migration already applied.")
            return

        print("Creating backup table...")
        # SQLite doesn't let us easily drop a UNIQUE constraint. 
        # We must create a new table, copy data, drop old, rename new.
        cursor.execute("""
            CREATE TABLE payments_new (
                id INTEGER NOT NULL PRIMARY KEY,
                order_id INTEGER,
                subscription_id INTEGER,
                provider_id INTEGER,
                amount FLOAT,
                payment_method VARCHAR(8),
                payment_status VARCHAR,
                transaction_id VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(order_id) REFERENCES orders (id),
                FOREIGN KEY(subscription_id) REFERENCES subscriptions (id),
                FOREIGN KEY(provider_id) REFERENCES providers (id)
            )
        """)
        
        print("Copying data...")
        # Since we modified the original model to have subscription_id, older data won't have it.
        # Ensure we map existing columns correctly.
        cursor.execute("""
            INSERT INTO payments_new (id, order_id, amount, payment_method, payment_status, transaction_id, created_at)
            SELECT id, order_id, amount, payment_method, payment_status, transaction_id, created_at FROM payments
        """)
        
        # Link existing payments to their respective provider_id via the orders table
        print("Linking provider_ids...")
        cursor.execute("""
            UPDATE payments_new
            SET provider_id = (SELECT provider_id FROM orders WHERE orders.id = payments_new.order_id)
            WHERE order_id IS NOT NULL
        """)
        
        print("Swapping tables...")
        cursor.execute("DROP TABLE payments")
        cursor.execute("ALTER TABLE payments_new RENAME TO payments")
        
        conn.commit()
        print("Migration successful: payments table updated.")
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

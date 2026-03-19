import sqlite3
import os

# Use absolute path for digibhoj.db
base_dir = r"d:\New folder\Dijibhojf"
db_path = os.path.join(base_dir, 'digibhoj.db')
print(f"Connecting to database at: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Add columns to delivery_agents
queries = [
    'ALTER TABLE delivery_agents ADD COLUMN current_lat FLOAT',
    'ALTER TABLE delivery_agents ADD COLUMN current_lng FLOAT'
]

for q in queries:
    try:
        cursor.execute(q)
        print(f"Executed: {q}")
    except Exception as e:
        print(f"Skipped {q}: {e}")

conn.commit()

# 2. Reset Order 1 and Agent 1 for testing
try:
    # Set Order 1 to out_for_delivery
    cursor.execute("UPDATE orders SET order_status = 'out_for_delivery' WHERE id = 1")
    # Set Agent 1 location
    cursor.execute("UPDATE delivery_agents SET current_lat = 18.5204, current_lng = 73.8567 WHERE id = 1")
    conn.commit()
    print("Reset Order 1 to 'out_for_delivery' and Agent 1 location.")
except Exception as e:
    print(f"Error resetting data: {e}")

conn.close()
print("Process finished.")

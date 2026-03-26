import sqlite3
import os

base_dir = r"d:\New folder\Dijibhojf"
db_path = os.path.join(base_dir, 'digibhoj.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE subscriptions ADD COLUMN payment_method VARCHAR')
    print("Added payment_method column")
except Exception as e:
    print(f"Skipped payment_method: {e}")

try:
    cursor.execute('ALTER TABLE subscriptions ADD COLUMN meal_id INTEGER REFERENCES meals(id)')
    print("Added meal_id column")
except Exception as e:
    print(f"Skipped meal_id: {e}")

conn.commit()
conn.close()

import sqlite3

def clean():
    conn = sqlite3.connect("d:\\New folder\\Dijibhojf\\digibhoj.db")
    cursor = conn.cursor()
    
    print("--- Searching for 'Mohit' in Users ---")
    cursor.execute("SELECT id, name, email FROM users WHERE name LIKE '%Mohit%' OR email LIKE '%mohit%'")
    rows = cursor.fetchall()
    for row in rows:
        print(f"Found: {row}")
        # Uncomment to delete if found
        # cursor.execute("DELETE FROM users WHERE id = ?", (row[0],))
        # print(f"Deleted user {row[0]}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    clean()

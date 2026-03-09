import sqlite3

def inspect_database():
    conn = sqlite3.connect('gg_bot.db')
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        print(f"\n=== {table_name.upper()} ===")

        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columns: {', '.join(columns)}")

        # Get all data
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        print(f"Rows: {len(rows)}")

        if rows:
            for row in rows[:5]:  # Show first 5 rows
                print(f"  {row}")
            if len(rows) > 5:
                print(f"  ... and {len(rows) - 5} more rows")
        else:
            print("  No data")

    conn.close()

if __name__ == "__main__":
    inspect_database()
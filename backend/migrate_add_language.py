import sqlite3
conn = sqlite3.connect('news_aggregator.db')
try:
    conn.execute("ALTER TABLE sources ADD COLUMN language TEXT DEFAULT 'en'")
    conn.commit()
    print('Migration complete: added language column to sources table')
except sqlite3.OperationalError as e:
    print(f'Already exists or error: {e}')
finally:
    conn.close()

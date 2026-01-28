# updates existing databases without certain new columns
import sqlite3

conn = sqlite3.connect('time_tracker.db')
cursor = conn.cursor()

# Add the new column
cursor.execute('ALTER TABLE time_sessions ADD COLUMN calendar_event_id TEXT')

conn.commit()
conn.close()

print("Database updated!")
import sqlite3
import os

db_path = 'c:/Users/yamin/CSProj12/smartpark.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE graph_nodes ADD COLUMN label VARCHAR DEFAULT ""')
        print("Migrated graph_nodes")
    except Exception as e:
        print("graph_nodes alter error:", e)
        
    try:
        c.execute('ALTER TABLE graph_edges ADD COLUMN manual_weight FLOAT')
        print("Migrated graph_edges")
    except Exception as e:
        print("graph_edges alter error:", e)
        
    conn.commit()
    conn.close()
    print("Migration complete.")
else:
    print("DB not found.")

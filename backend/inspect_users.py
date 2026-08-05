import sqlite3
import os
DB = os.path.join(os.path.dirname(__file__), 'sirkome_bank.db')
print('DB exists:', os.path.exists(DB))
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT id,name,email,password,account_number FROM users').fetchall()
print('rows:', len(rows))
for row in rows:
    print(dict(row))
conn.close()

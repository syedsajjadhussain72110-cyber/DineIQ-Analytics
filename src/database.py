from pathlib import Path
import sqlite3,os,json
from werkzeug.security import generate_password_hash
ROOT=Path(__file__).resolve().parents[1]
def connect(path=None):
 dbpath=Path(path) if path else ROOT/'database/app.db'
 dbpath.parent.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(dbpath,timeout=30);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');return c
def init(path=None):
 with connect(path) as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,role TEXT);CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user_id INTEGER,action TEXT,details TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,kind TEXT,status TEXT,details TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,finished_at TEXT);CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY,value TEXT);CREATE TABLE IF NOT EXISTS results(name TEXT PRIMARY KEY,payload TEXT);CREATE TABLE IF NOT EXISTS recommendations(id INTEGER PRIMARY KEY,payload TEXT);''')
  if not c.execute('SELECT 1 FROM users LIMIT 1').fetchone():
   password=os.getenv('DINEIQ_DEMO_PASSWORD','DineIQ-Demo-2026!')
   for user,role in [('admin','administrator'),('analyst','analyst'),('manager','manager'),('regional','regional_manager')]:c.execute('INSERT INTO users(username,password,role) VALUES(?,?,?)',(user,generate_password_hash(password),role))
def audit(user,action,details='',path=None):
 with connect(path) as c:c.execute('INSERT INTO audit(user_id,action,details) VALUES(?,?,?)',(user,action,str(details)[:4000]))
def sync(path=None):
 init(path)
 with connect(path) as c:
  for p in (ROOT/'reports').glob('*.json'):c.execute('INSERT OR REPLACE INTO results(name,payload) VALUES(?,?)',(p.stem,p.read_text(encoding='utf-8')))
  import pandas as pd
  if (ROOT/'reports/recommendations.csv').exists():
   c.execute('DELETE FROM recommendations');c.executemany('INSERT INTO recommendations(payload) VALUES(?)',[(json.dumps(x),) for x in pd.read_csv(ROOT/'reports/recommendations.csv').to_dict('records')])
if __name__=='__main__':sync()

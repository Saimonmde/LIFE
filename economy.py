# SPDX-License-Identifier: AGPL-3.0-or-later
"""Finite test currency: SQLite transactions, server ore credits, append-only journal."""
import hashlib,json,os,secrets,sqlite3,time
RECIPES={'mineral_cobre':(3,4),'mineral_plata':(4,12),'mineral_oro':(5,30)}
LAYOUT={'cobre':[(6,6),(9,4),(5,12),(8,22),(12,8)],'plata':[(27,5),(30,10),(28,22),(24,9)],'oro':[(5,3),(17,3),(28,3),(32,17),(3,18),(24,27)]}
ROCKS={f'mina_{metal}_{i}':(x,y,'mineral_'+metal,32 if metal=='oro' else 18) for metal,coords in LAYOUT.items() for i,(x,y) in enumerate(coords)}
class Economy:
 def __init__(self,path,supply=21000000):
  os.makedirs(os.path.dirname(os.path.abspath(path)),exist_ok=True)
  self.db=sqlite3.connect(path,isolation_level=None);self.db.row_factory=sqlite3.Row
  self.db.executescript('''PRAGMA journal_mode=WAL;PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,secret TEXT UNIQUE,balance INTEGER NOT NULL CHECK(balance>=0));
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS ores(wallet TEXT,item TEXT,qty INTEGER NOT NULL CHECK(qty>=0),PRIMARY KEY(wallet,item));
CREATE TABLE IF NOT EXISTS cooldown(wallet TEXT,node TEXT,until REAL,PRIMARY KEY(wallet,node));
CREATE TABLE IF NOT EXISTS journal(seq INTEGER PRIMARY KEY,at INTEGER,source TEXT,destination TEXT,amount INTEGER CHECK(amount>0),reason TEXT,previous TEXT,hash TEXT);
CREATE TABLE IF NOT EXISTS receipts(wallet TEXT,id TEXT,result TEXT,PRIMARY KEY(wallet,id));
CREATE TRIGGER IF NOT EXISTS journal_no_update BEFORE UPDATE ON journal BEGIN SELECT RAISE(ABORT,'append-only');END;
CREATE TRIGGER IF NOT EXISTS journal_no_delete BEFORE DELETE ON journal BEGIN SELECT RAISE(ABORT,'append-only');END;
''')
  self.db.execute('BEGIN IMMEDIATE')
  try:
   if not self.db.execute("SELECT 1 FROM meta WHERE key='supply'").fetchone():
    if type(supply)!=int or supply<1:raise ValueError('Invalid supply')
    self.db.execute("INSERT INTO meta VALUES('supply',?)",(supply,));self.db.execute("INSERT INTO accounts VALUES('treasury',NULL,?)",(supply,))
   self.db.execute('COMMIT')
  except Exception:self.db.execute('ROLLBACK');raise
 def wallet(self,token=None):
  if isinstance(token,str) and len(token)<200:
   row=self.db.execute('SELECT id FROM accounts WHERE secret=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
   if row:return row[0],token
  token=secrets.token_urlsafe(32);wallet=secrets.token_hex(12)
  self.db.execute('INSERT INTO accounts VALUES(?,?,0)',(wallet,hashlib.sha256(token.encode()).hexdigest()))
  return wallet,token
 def snapshot(self,wallet):
  supply=self.db.execute("SELECT value FROM meta WHERE key='supply'").fetchone()[0];treasury=self.db.execute("SELECT balance FROM accounts WHERE id='treasury'").fetchone()[0]
  return {'balance':self.db.execute('SELECT balance FROM accounts WHERE id=?',(wallet,)).fetchone()[0],'supply':supply,'treasury':treasury,'circulating':supply-treasury,'ores':dict(self.db.execute('SELECT item,qty FROM ores WHERE wallet=?',(wallet,))), 'journal':[dict(r) for r in self.db.execute('SELECT seq,at,amount,reason,hash FROM journal WHERE destination=? ORDER BY seq DESC LIMIT 20',(wallet,))]}
 def act(self,wallet,message,zone,x,y):
  request=message.get('request');kind=message.get('action')
  if not isinstance(request,str) or not 8<=len(request)<=80:raise ValueError('Solicitud inválida')
  self.db.execute('BEGIN IMMEDIATE')
  try:
   cached=self.db.execute('SELECT result FROM receipts WHERE wallet=? AND id=?',(wallet,request)).fetchone()
   if cached:result=json.loads(cached[0])
   elif kind=='mine':
    node=message.get('node');rock=ROCKS.get(node)
    if not rock or zone!='mine' or max(abs(x-rock[0]),abs(y-rock[1]))>1.6:raise ValueError('Acércate a la roca dentro de la mina')
    row=self.db.execute('SELECT until FROM cooldown WHERE wallet=? AND node=?',(wallet,node)).fetchone()
    if row and row[0]>time.time():raise ValueError('Esta veta aún se está regenerando')
    item=rock[2];qty=2
    self.db.execute('INSERT INTO ores VALUES(?,?,?) ON CONFLICT(wallet,item) DO UPDATE SET qty=qty+excluded.qty',(wallet,item,qty))
    self.db.execute('INSERT INTO cooldown VALUES(?,?,?) ON CONFLICT(wallet,node) DO UPDATE SET until=excluded.until',(wallet,node,time.time()+rock[3]))
    result={'item':item,'qty':qty}
   elif kind=='forge':
    item=message.get('item');batches=message.get('batches');mode=message.get('mode')
    if zone!='mine' or max(abs(x-18),abs(y-15))>1.6:raise ValueError('Acércate al horno central de la mina')
    if item not in RECIPES or type(batches)!=int or not 1<=batches<=1000 or mode not in ('coins','ingot'):raise ValueError('Receta inválida')
    ore,coins=RECIPES[item];cost=ore*batches;amount=coins*batches if mode=='coins' else 0
    row=self.db.execute('SELECT qty FROM ores WHERE wallet=? AND item=?',(wallet,item)).fetchone()
    if not row or row[0]<cost:raise ValueError('Se necesitan minerales recogidos en línea en esta mina; los guardados anteriores no están verificados')
    if amount:
     changed=self.db.execute("UPDATE accounts SET balance=balance-? WHERE id='treasury' AND balance>=?",(amount,amount)).rowcount
     if not changed:raise ValueError('La tesorería no tiene monedas disponibles')
     self.db.execute('UPDATE accounts SET balance=balance+? WHERE id=?',(amount,wallet))
     prev=self.db.execute('SELECT hash FROM journal ORDER BY seq DESC LIMIT 1').fetchone();prev=prev[0] if prev else 'genesis';at=int(time.time());reason=f'fundicion:{item}:{batches}'
     digest=hashlib.sha256(json.dumps([at,'treasury',wallet,amount,reason,prev],separators=(',',':')).encode()).hexdigest()
     self.db.execute("INSERT INTO journal(at,source,destination,amount,reason,previous,hash) VALUES(?,'treasury',?,?,?,?,?)",(at,wallet,amount,reason,prev,digest))
    self.db.execute('UPDATE ores SET qty=qty-? WHERE wallet=? AND item=?',(cost,wallet,item));result={'coins':amount,'cost':cost,'qty':batches,'item':item,'mode':mode}
   else:raise ValueError('Acción desconocida')
   if not cached:self.db.execute('INSERT INTO receipts VALUES(?,?,?)',(wallet,request,json.dumps(result)))
   self.db.execute('COMMIT');return result
  except Exception:self.db.execute('ROLLBACK');raise

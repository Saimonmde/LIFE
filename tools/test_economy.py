# SPDX-License-Identifier: AGPL-3.0-or-later
import sys,tempfile,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from economy import Economy
with tempfile.TemporaryDirectory() as d:
 path=d+'/ledger.sqlite3';e=Economy(path,100);w,token=e.wallet();assert e.wallet(token)[0]==w
 def mine(node,request,x,y):return e.act(w,dict(action='mine',node=node,request=request),'mine',x,y)
 mine('mina_cobre_0','mine-0001',6,7)
 assert mine('mina_cobre_0','mine-0001',6,7)['qty']==2
 try:mine('mina_cobre_0','mine-0002',6,7);assert False
 except ValueError:pass
 mine('mina_cobre_1','mine-0003',9,5)
 action=dict(action='forge',item='mineral_cobre',batches=1,mode='coins',request='forge-0001')
 assert e.act(w,action,'mine',18,16)['coins']==4
 e.act(w,action,'mine',18,16)
 snap=e.snapshot(w);assert snap['balance']==4 and snap['treasury']==96 and len(snap['journal'])==1 and snap['ores']['mineral_cobre']==1
 for message,zone,x,y in [(dict(action,request='forge-0002'), 'mine',18,16),(dict(action,request='forge-0003',batches=-1),'mine',18,16),(dict(action,request='forge-0004'),'city',18,16)]:
  try:e.act(w,message,zone,x,y);assert False
  except ValueError:pass
 assert e.snapshot(w)==snap
 try:e.db.execute('DELETE FROM journal');assert False
 except sqlite3.IntegrityError:pass
 e.db.close();e=Economy(path,99999);assert e.snapshot(w)['supply']==100 and e.snapshot(w)['balance']==4
 assert e.db.execute('SELECT sum(balance) FROM accounts').fetchone()[0]==100
 print('PASS: suministro conservado, persistencia, identidad por token, idempotencia, cooldown y rechazo sin consumir recursos.')

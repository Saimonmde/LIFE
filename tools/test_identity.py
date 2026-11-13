# SPDX-License-Identifier: AGPL-3.0-or-later
"""Email access and server-owned nicknames without migrating or deleting saves."""
import asyncio,copy,json,os,sys,unittest
sys.path.insert(0,os.path.dirname(__file__))
import accounts as acc
class IdentityTests(unittest.TestCase):
 def signup(self,doc,name,email,now=100):
  sent={}
  acc.begin_signup(doc,name,email,'','long-password',lambda email,code:sent.update(code=code),lambda phone:self.fail('SMS for email-only account'),now=now)
  return sent['code']
 def test_email_only_login_and_stable_avatar(self):
  doc=acc.empty();code=self.signup(doc,'Ana','ana@example.com')
  result=acc.verify_signup(doc,'ana@example.com',code,'',lambda *args:self.fail('No phone verification expected'),now=101)
  user=doc['users'][0];user.update(wallet_name='LegacyWallet',wallet_token='existing-secret',progress={'xp':120,'inv':['pico']})
  original=copy.deepcopy(user)
  again=acc.login_password(doc,' ANA@example.com ','long-password',now=102)
  self.assertEqual(again['user']['id'],result['user']['id']);self.assertEqual(again['user']['avatar_id'],result['user']['avatar_id'])
  self.assertEqual(again['user']['wallet_name'],'LegacyWallet');self.assertEqual(user,original)
  with self.assertRaises(acc.AuthError):acc.login_password(doc,'ana@example.com',again['user']['avatar_id'],now=103)
 def test_pending_and_verified_names_are_case_insensitive(self):
  doc=acc.empty();code=self.signup(doc,'Simón','one@example.com')
  with self.assertRaises(acc.AuthError):self.signup(doc,'SIMÓN','two@example.com')
  acc.verify_signup(doc,'one@example.com',code,'',lambda *args:True,now=101)
  with self.assertRaises(acc.AuthError):self.signup(doc,'simón','two@example.com',now=102)
  self.assertEqual(acc.name_key('  A  B '),acc.name_key('a b'))
 def test_oauth_collision_preserves_existing_account(self):
  doc=acc.empty();code=self.signup(doc,'Ana','one@example.com');acc.verify_signup(doc,'one@example.com',code,'',lambda *args:True,now=101)
  state=acc.start_oauth(doc,'google',now=110);r=acc.finish_oauth(doc,'google',state,state,{'sub':'g-other','email':'two@example.com','name':'ANA'},now=111)
  self.assertNotEqual(acc.name_key(r['user']['name']),'ana');self.assertEqual(doc['users'][0]['name'],'Ana')
 def test_verify_checks_name_again_after_oauth_race(self):
  doc=acc.empty();code=self.signup(doc,'Ana','one@example.com')
  doc['users'].append({'id':'existing','name':'ANA','email':'other@example.com'})
  with self.assertRaises(acc.AuthError):acc.verify_signup(doc,'one@example.com',code,'',lambda *args:True,now=101)
  self.assertEqual(len(doc['users']),1)
 def test_login_attempts_and_nickname_are_not_credentials(self):
  doc=acc.empty()
  for i in range(5):
   with self.assertRaises(acc.AuthError):acc.login_password(doc,'nobody@example.com','guess',now=100+i)
  with self.assertRaises(acc.AuthError):acc.login_password(doc,'nobody@example.com','guess',now=106)
  self.assertTrue(doc['rates']['login:nobody@example.com'])
 def test_http_login_cookie_and_reserved_guest_name(self):
  sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)));import server as s
  doc=acc.empty();code=self.signup(doc,'Ana','one@example.com');acc.verify_signup(doc,'one@example.com',code,'',lambda *args:True,now=101)
  previous=(s.ACCOUNTS,s.save_accounts,s.clients);s.ACCOUNTS=doc;s.save_accounts=lambda:None;s.clients={}
  try:
   body=json.dumps({'email':'one@example.com','password':'long-password'}).encode()
   response=asyncio.run(s.try_auth('POST','/auth/entrar','/auth/entrar',{},body))
   self.assertIn(b'200 OK',response);self.assertIn(b'HttpOnly',response);self.assertNotIn(b'password_hash',response)
   guest=type('Guest',(),{'id':1,'user':None})()
   self.assertNotEqual(acc.name_key(s.unique_name('ANA',guest)),'ana')
   owner=type('Owner',(),{'id':2,'user':doc['users'][0]})()
   self.assertEqual(s.unique_name('ignored',owner),'Ana')
  finally:s.ACCOUNTS,s.save_accounts,s.clients=previous
if __name__=='__main__':unittest.main()

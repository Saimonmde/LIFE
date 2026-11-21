# SPDX-License-Identifier: AGPL-3.0-or-later
"""La Mina de La Ladera cabe más gente, una veta por persona, y paga sólo SMC."""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as eco
import mina_ladera as ladera
import mundos
import nodos
import supply as sup
import viajes

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
NOW = 1_700_000_000


def world():
    with open(os.path.join(ROOT, 'data', 'el-jardin.json'), encoding='utf-8') as handle:
        return json.load(handle)


def fresh():
    econ = eco.empty_state()
    sup.ensure(econ, now=NOW)
    return econ


class LaderaTests(unittest.TestCase):
    def test_capacity_is_larger_and_one_vein_per_player(self):
        self.assertGreater(ladera.capacity(), len(nodos.MINE))
        self.assertEqual(ladera.capacity(), 47)
        self.assertEqual(len(ladera.VEINS), 47)
        spots = [(row[0], row[1]) for row in ladera.VEINS.values()]
        self.assertEqual(len(spots), len(set(spots)))
        for node_id, (x, y, ms, metal) in ladera.VEINS.items():
            self.assertGreaterEqual(x, 2)
            self.assertGreaterEqual(y, 2)
            self.assertLess(x, ladera.WIDTH - 2)
            self.assertLess(y, ladera.HEIGHT - 2)
            self.assertEqual(nodos.millis([], node_id), ms)
            self.assertEqual(ladera.metal_of(node_id), metal)
        state = nodos.empty()
        ids = sorted(ladera.VEINS)
        for index, node_id in enumerate(ids):
            claim = nodos.claim(state, 3, node_id, 'p%d' % index, NOW)
            self.assertTrue(claim['ok'], node_id)
            self.assertTrue(claim['tracked'])
        busy = nodos.claim(state, 3, ids[0], 'extra', NOW + 0.1)
        self.assertFalse(busy['ok'])
        self.assertEqual(busy['reason'], 'ocupado')
        same = nodos.claim(state, 3, ids[1], 'p0', NOW + 0.1)
        self.assertEqual(same['reason'], 'una')
        nodos.finish(state, 3, ids[0], 'p0', NOW)
        resting = nodos.claim(state, 3, ids[0], 'extra', NOW + 1)
        self.assertEqual(resting['reason'], 'agotada')
        other = nodos.claim(state, 5, ids[2], 'otro-mundo', NOW + 1)
        self.assertTrue(other['ok'])

    def test_payouts_are_smc_only_and_keep_the_caps(self):
        econ = fresh()
        quiet = ladera.cobrar(econ, 'Jay', 'jay', 'cobre', NOW)
        self.assertTrue(quiet['ok'])
        self.assertEqual(quiet['smh'], 0)
        self.assertIn('0,001 SMC', quiet['texto'])
        self.assertEqual(econ['wallets'].get('Jay', 0), 0)
        for _ in range(8):
            step = ladera.cobrar(econ, 'Jay', 'jay', 'cobre', NOW)
            self.assertEqual(step['smh'], 0)
        tenth = ladera.cobrar(econ, 'Jay', 'jay', 'cobre', NOW)
        self.assertEqual(tenth['smh'], 1)
        self.assertIn('0,01 SMC', tenth['texto'])
        self.assertEqual(econ['wallets']['Jay'], 1)

        silver = ladera.cobrar(econ, 'Sol', 'sol', 'plata', NOW)
        self.assertEqual(silver['smh'], 1)
        self.assertIn('0,01 SMC', silver['texto'])
        gold = ladera.cobrar(econ, 'Sol', 'sol', 'oro', NOW)
        self.assertEqual(gold['smh'], 10)
        self.assertIn('0,1 SMC', gold['texto'])
        self.assertEqual(econ['wallets']['Sol'], 11)
        for text in (quiet['texto'], tenth['texto'], silver['texto'], gold['texto']):
            upper = text.upper()
            self.assertNotIn('SMH', upper)
            self.assertNotIn('SMP', upper)
            self.assertNotIn('SPH', upper)
            self.assertNotIn('SIMONPLATA', upper)

        capped = fresh()
        sup.ensure(capped, now=NOW)
        acc = sup._account(capped['supply'], 'jay', NOW)
        acc['earned'] = sup.enforced_daily_smh(0, 0, 0) - 10
        roomy = ladera.cobrar(capped, 'Jay', 'jay', 'oro', NOW)
        self.assertEqual(roomy['smh'], 10)
        blocked = ladera.cobrar(capped, 'Jay', 'jay', 'oro', NOW)
        self.assertFalse(blocked['ok'])
        self.assertEqual(blocked['reason'], 'cap')
        silver_blocked = ladera.cobrar(capped, 'Jay', 'jay', 'plata', NOW)
        self.assertEqual(silver_blocked['reason'], 'cap')

        copper = fresh()
        sup.ensure(copper, now=NOW)
        box = sup._account(copper['supply'], 'jay', NOW)
        box['copperEarned'] = sup.copper_daily_smh()
        copper['minaLadera'] = {'jay': {'millis': 9}}
        denied = ladera.cobrar(copper, 'Jay', 'jay', 'cobre', NOW)
        self.assertEqual(denied['reason'], 'cap')
        self.assertEqual(copper['wallets'].get('Jay', 0), 0)
        self.assertEqual(copper['minaLadera']['jay']['millis'], 9)

        full = fresh()
        full['minedSmh'] = eco.issuance_room(full)
        stopped = ladera.cobrar(full, 'Jay', 'jay', 'oro', NOW)
        self.assertEqual(stopped['reason'], 'supply')
        self.assertEqual(full['wallets'].get('Jay', 0), 0)
        self.assertIn('21.000.000', stopped['texto'])

    def test_entrance_is_beside_the_crops_and_on_the_map(self):
        ground = world()
        spot = ladera.entrance(ground)
        self.assertEqual((spot['x'], spot['y']), (150, 202))
        stand = viajes.ladera_stand(ground)
        self.assertEqual(stand['name'], 'Mina de La Ladera')
        self.assertEqual((stand['x'], stand['y']), (150, 203))
        self.assertTrue(viajes.walkable(ground, stand['x'], stand['y']))
        first = viajes.mine_stand(ground)
        self.assertGreaterEqual(max(abs(stand['x'] - first['x']), abs(stand['y'] - first['y'])), 8)
        resolved = viajes.resolve(ground, 'mina_ladera')
        self.assertEqual(resolved['recurso'], ladera.RECURSO)
        self.assertIn('0,001', resolved['recurso'])
        self.assertIn('0,1', resolved['recurso'])
        with open(os.path.join(ROOT, 'play', 'game.js'), encoding='utf-8') as handle:
            page = handle.read()
        self.assertIn("'mina_ladera'", page)
        self.assertIn('pico_ladera', page)
        with open(os.path.join(ROOT, 'play', 'baul.js'), encoding='utf-8') as handle:
            baul = handle.read()
        self.assertIn("here !== 'mina2'", baul)
        self.assertIn("typeof ink.world === 'function'", baul)

    def test_cousins_in_world_three_see_each_other_only_inside(self):
        jay = type('P', (), {'world': 3, 'place': 'mina-ladera', 'zone': 'mina2'})()
        primo = type('P', (), {'world': 3, 'place': 'mina-ladera', 'zone': 'mina2'})()
        self.assertTrue(mundos.same_sight(jay, primo))
        primo.world = 1
        self.assertFalse(mundos.same_sight(jay, primo))
        primo.world = 3
        primo.place = 'mina-palmas'
        self.assertFalse(mundos.same_sight(jay, primo))
        self.assertEqual(mundos.place_of(0, 0, 'mina2', []), 'mina-ladera')
        self.assertIn('mina-ladera', mundos.SHARED_INTERIOR)

    def test_client_layout_matches(self):
        run = subprocess.run(
            ['node', '-e', """
const fs = require('fs');
const vm = require('vm');
const world = JSON.parse(fs.readFileSync('data/el-jardin.json', 'utf8'));
const ctx = { console, module: {}, exports: {} };
vm.runInNewContext(fs.readFileSync('play/galerias.js', 'utf8'), ctx);
vm.runInNewContext(fs.readFileSync('play/mina-ladera.js', 'utf8'), ctx);
const api = ctx.MinaLadera;
const door = api.entrance(world);
const layout = api.spots();
const cave = api.cave(1);
if (api.capacity() !== 47) process.exit(2);
if (!door || door.x !== 150 || door.y !== 202) process.exit(3);
const ids = cave.nodes.filter(n => n.type === 'mineral_rock').map(n => n.id);
if (ids.length !== 47) process.exit(4);
const chest = cave.nodes.find(n => n.type === 'mine_chest' && n.id === 'baul_mina');
const furnace = cave.nodes.find(n => n.type === 'furnace' && n.id === 'horno_ladera');
if (!chest || !furnace) process.exit(5);
if (Math.max(Math.abs(furnace.x - chest.x), Math.abs(furnace.y - chest.y)) > 4) process.exit(8);
const metals = { cobre: 0, plata: 0, oro: 0 };
ids.forEach(id => { metals[id.split('_')[1]]++; });
if (metals.cobre !== 16 || metals.plata !== 13 || metals.oro !== 18) process.exit(6);
if (layout.cobre.length + layout.plata.length + layout.oro.length !== 47) process.exit(7);
console.log('ok');
"""],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('ok', run.stdout)

    def test_furnace_is_beside_the_chest_and_checks_distance(self):
        self.assertEqual(ladera.HORNO, (24, 16))
        self.assertEqual(ladera.REACH, 1)
        self.assertNotIn(ladera.HORNO, [(row[0], row[1]) for row in ladera.VEINS.values()])
        self.assertTrue(ladera.junto('mina2', 24, 16))
        self.assertTrue(ladera.junto('mina2', 25, 17))
        self.assertTrue(ladera.junto('mina2', 23.2, 16.4))
        self.assertFalse(ladera.junto('mina2', 24, 18))
        self.assertFalse(ladera.junto('mina2', 21, 18))
        self.assertFalse(ladera.junto('mine', 24, 16))
        self.assertFalse(ladera.junto('city', 25, 16))
        self.assertFalse(ladera.junto('mina2', None, 16))
        self.assertEqual(ladera.PIEZAS, {'oro': 10, 'plata': 100, 'cobre': 1000})
        self.assertEqual(ladera.partir(ladera.millis_de('oro', 1)), (10, 0))
        self.assertEqual(ladera.partir(ladera.millis_de('plata', 1)), (1, 0))
        self.assertEqual(ladera.partir(ladera.millis_de('cobre', 9, 0)), (0, 9))
        self.assertEqual(ladera.partir(ladera.millis_de('cobre', 1, 9)), (1, 0))

    def test_smelting_counts_the_shared_daily_cap_once(self):
        econ = fresh()
        econ['supply']['bits'] = 4
        who = {
            'account': 'jay', 'ip': '198.51.100.40', 'age': 0, 'play': 0,
            'quests': 0, 'activity': 8, 'fresh': True,
        }
        opened = sup.open_challenge(econ, who, 'acunar', 'ladera:simoncoin:1', now=NOW)
        self.assertTrue(opened['ok'], opened.get('reason'))
        proof = dict(opened['challenge'])
        proof['nonce'] = sup.search_nonce(proof['payload'], proof['bits'])
        checked = sup.redeem(
            econ, who, 'acunar', 'ladera:simoncoin:1', proof,
            want_smh=10, now=NOW + 1, reserve=False, pay_request=True,
        )
        self.assertTrue(checked['ok'], checked.get('reason'))
        acc = sup._account(econ['supply'], 'jay', NOW + 1)
        self.assertEqual(int(acc.get('earned') or 0), 0)
        self.assertEqual(int(acc.get('copperEarned') or 0), 0)
        first = ladera.contar(econ, 'jay', 'oro', checked['smh'], NOW + 1, checked['proof'])
        self.assertEqual(first, 10)
        self.assertEqual(int(acc['earned']), 10)
        again = ladera.contar(econ, 'jay', 'oro', 10, NOW + 1, checked['proof'])
        self.assertEqual(again, 0)
        self.assertEqual(int(acc['earned']), 10)
        replay = sup.redeem(
            econ, who, 'acunar', 'ladera:simoncoin:1', proof,
            want_smh=10, now=NOW + 2, reserve=False, pay_request=True,
        )
        self.assertEqual(replay.get('reason'), 'replay')
        self.assertEqual(int(acc['earned']), 10)
        silver = ladera.contar(econ, 'jay', 'plata', 5, NOW + 2, 'plata-1')
        self.assertEqual(silver, 5)
        self.assertEqual(int(acc['earned']), 15)
        self.assertEqual(int(acc.get('copperEarned') or 0), 0)
        copper = ladera.contar(econ, 'jay', 'cobre', 1, NOW + 2, 'cobre-1')
        self.assertEqual(copper, 1)
        self.assertEqual(int(acc['earned']), 15)
        self.assertEqual(int(acc['copperEarned']), 1)
        with open(os.path.join(ROOT, 'server.py'), encoding='utf-8') as handle:
            page = handle.read()
        hook = page.split('def acunar_ladera')[1].split('\ndef eco_room_agotado')[0]
        self.assertEqual(hook.count('LADERA.contar('), 1)
        self.assertIn('reserve=False', hook)
        self.assertIn('LADERA.junto', hook)
        self.assertNotIn('cobrar', hook)
        smelt = page.split('def smelt_for')[1].split('\ndef ')[0]
        self.assertLess(smelt.find("== 'mina2'"), smelt.find('take_proof'))
        pico = page.split('def pico_ladera')[1].split('\ndef ')[0]
        self.assertNotIn('cobrar', pico)
        with open(os.path.join(ROOT, 'play', 'acunar.js'), encoding='utf-8') as handle:
            dialog = handle.read()
        self.assertIn("world.mapId === 'mina2'", dialog)

    def test_migration_keeps_wallet_and_unpaid_dust(self):
        econ = fresh()
        eco.credit(econ, 'Jay', 25)
        econ['minaLadera'] = {'jay': {'millis': 7}}
        self.assertTrue(ladera.migrar(econ))
        self.assertEqual(econ['wallets']['Jay'], 25)
        self.assertEqual(econ['minaLadera']['jay']['millis'], 7)
        self.assertFalse(ladera.migrar(econ))
        self.assertEqual(econ['wallets']['Jay'], 25)
        self.assertEqual(econ['minaLadera']['jay']['millis'], 7)


if __name__ == '__main__':
    unittest.main()

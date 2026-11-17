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
        self.assertEqual(ladera.capacity(), 30)
        self.assertEqual(len(ladera.VEINS), 30)
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
vm.runInNewContext(fs.readFileSync('play/mina-ladera.js', 'utf8'), ctx);
const api = ctx.MinaLadera;
const door = api.entrance(world);
const layout = api.spots();
const cave = api.cave(1);
if (api.capacity() !== 30) process.exit(2);
if (!door || door.x !== 150 || door.y !== 202) process.exit(3);
const ids = cave.nodes.filter(n => n.type === 'mineral_rock').map(n => n.id);
if (ids.length !== 30) process.exit(4);
if (!cave.nodes.some(n => n.type === 'mine_chest' && n.id === 'baul_mina')) process.exit(5);
const metals = { cobre: 0, plata: 0, oro: 0 };
ids.forEach(id => { metals[id.split('_')[1]]++; });
if (metals.cobre !== 10 || metals.plata !== 8 || metals.oro !== 12) process.exit(6);
if (layout.cobre.length + layout.plata.length + layout.oro.length !== 30) process.exit(7);
console.log('ok');
"""],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('ok', run.stdout)


if __name__ == '__main__':
    unittest.main()

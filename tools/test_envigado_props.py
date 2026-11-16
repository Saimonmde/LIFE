# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cada banca, caneca y escultura entra en la lista 2D y en la lista 3D."""
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED = [
    'caneca_0', 'caneca_1', 'caneca_2',
    'banca_norte', 'banca_oriente', 'banca_sur', 'banca_esquina',
    'banca_sendero_oeste', 'banca_sendero_este', 'banca_sendero_sur',
    'banca_cruce_oeste', 'banca_cruce_este', 'banca_cruce_suroeste',
    'banca_atrio_1', 'banca_atrio_2',
    'anillo', 'columna', 'ovalo',
    'banca_caldas_este', 'banca_caldas_sur',
    'banca_sabaneta_este', 'banca_sabaneta_sur',
    'banca_la_estrella_este', 'banca_la_estrella_sur',
    'banca_itagui_este', 'banca_itagui_sur',
    'banca_medellin_este', 'banca_medellin_sur',
    'banca_bello_este', 'banca_bello_sur',
    'banca_copacabana_este', 'banca_copacabana_sur',
    'banca_girardota_este', 'banca_girardota_sur',
    'banca_barbosa_este', 'banca_barbosa_sur',
]


class ParkPropTests(unittest.TestCase):
    def test_every_prop_is_in_both_scene_lists(self):
        script = r"""
const fs = require('fs');
const window = { Casa: { VALLE_OFFSET: { x: -133, y: 203 } } };
global.window = window;
eval(fs.readFileSync('play/envigado-park.js', 'utf8'));
const park = window.EnvigadoPark;
const props = park.allProps();
const ctx = { save(){}, restore(){}, beginPath(){}, arc(){}, stroke(){}, ellipse(){}, fill(){}, fillRect(){} };
park.drawn2d.length = 0;
for (const prop of props) park.paint2d(ctx, prop, 64);
const three = fs.readFileSync('play/envigado-props.js', 'utf8');
if (!three.includes('for (const prop of park.allProps())')) process.exit(2);
if (!three.includes('park.drawn3d.push(prop.id)')) process.exit(3);
if (!three.includes('g.name = prop.id')) process.exit(4);
if (/caneca_envigado|id==='poblado'|name:\\s*'poblado'/i.test(three)) process.exit(5);
process.stdout.write(props.map(p => p.id).join(',') + '\n' + park.drawn2d.join(','));
"""
        out = subprocess.check_output(['node', '-e', script], cwd=ROOT, text=True)
        made, drawn = out.strip().split('\n')
        self.assertEqual(made.split(','), EXPECTED)
        self.assertEqual(drawn.split(','), EXPECTED)
        props = open(os.path.join(ROOT, 'play', 'envigado-props.js'), encoding='utf-8').read()
        game = open(os.path.join(ROOT, 'play', 'game.js'), encoding='utf-8').read()
        self.assertIn('EnvigadoPark.allProps()', game)
        self.assertIn('EnvigadoPark.paint2d', game)
        self.assertNotIn('poblado', props.lower())
        self.assertIn('banca_envigado.glb', props)
        self.assertIn('InstancedMesh', props)
        self.assertIn('benchProxyGeometry', props)
        self.assertIn('length: 1.443', props)
        self.assertIn('seat: 0.465', props)
        self.assertIn('Banca de sentarse', props)

    def test_benches_block_their_tile_and_leave_the_door_open(self):
        script = r"""
const fs = require('fs');
const window = { Casa: { VALLE_OFFSET: { x: -133, y: 203 } } };
global.window = window;
eval(fs.readFileSync('play/envigado-park.js', 'utf8'));
const park = window.EnvigadoPark;
const W = { width: 351, height: 382, collision: Array.from({length: 382}, () => Array(351).fill(0)) };
park.block(W);
const benches = park.allProps().filter(p => p.kind === 'banca');
if (benches.length < 12) process.exit(2);
for (const bench of benches) {
  if (W.collision[bench.y][bench.x] !== 1) process.exit(3);
}
for (const [x, y] of [[93, 267], [92, 268], [94, 267]]) {
  if (W.collision[y][x] !== 0) process.exit(4);
}
const spec = JSON.parse(fs.readFileSync('graphics/models/banca_envigado.json', 'utf8'));
if (spec.largo !== 1.443 || spec.ancho !== 0.433 || spec.alto !== 0.465) process.exit(5);
process.stdout.write(String(benches.length));
"""
        out = subprocess.check_output(['node', '-e', script], cwd=ROOT, text=True)
        self.assertEqual(out.strip(), '30')


if __name__ == '__main__':
    unittest.main()

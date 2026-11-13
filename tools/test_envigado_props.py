# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cada banca, caneca y escultura entra en la lista 2D y en la lista 3D."""
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED = [
    'caneca_0', 'caneca_1', 'caneca_2',
    'banca_norte', 'banca_oriente', 'banca_sur', 'banca_esquina',
    'anillo', 'columna', 'ovalo',
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


if __name__ == '__main__':
    unittest.main()

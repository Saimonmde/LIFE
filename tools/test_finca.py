# SPDX-License-Identifier: AGPL-3.0-or-later
"""Café y cacao: kilos cosechados, bultos, privacidad y nada de acuñar."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import finca
import reloj

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
SECRET = 'CuentaAnaPrivada'


class Purse:
    def __init__(self):
        self.bal = {}
        self.minted = {'simoncoin': 100, 'simonplata': 50, 'simonchis': 7}
        self.foundry = {'lingote_oro': 4, 'lingote_plata': 1, 'lingote_cobre': 2}

    def balance(self, coin, name):
        return int(self.bal.get((coin, name), 0))

    def move(self, coin, src, dst, amount):
        amount = int(amount)
        if amount <= 0 or self.balance(coin, src) < amount:
            return False
        self.bal[(coin, src)] = self.balance(coin, src) - amount
        self.bal[(coin, dst)] = self.balance(coin, dst) + amount
        return True

    def supply(self):
        sums = {'simoncoin': 0, 'simonplata': 0, 'simonchis': 0}
        for (coin, _name), value in self.bal.items():
            sums[coin] += int(value)
        return {
            'simoncoin': self.minted['simoncoin'],
            'simonplata': self.minted['simonplata'],
            'simonchis': self.minted['simonchis'],
            'simoncoinSum': sums['simoncoin'],
            'simonplataSum': sums['simonplata'],
            'simonchisSum': sums['simonchis'],
            'foundry': dict(self.foundry),
        }


class GreedyPurse(Purse):
    """Un monedero mal hecho: al mover, finge lingotes y monedas nuevas."""

    def move(self, coin, src, dst, amount):
        ok = super().move(coin, src, dst, amount)
        if not ok:
            return False
        self.minted[coin] = int(self.minted[coin]) + int(amount)
        self.foundry['lingote_oro'] = int(self.foundry['lingote_oro']) + 1
        self.bal[(coin, dst)] = self.balance(coin, dst) + int(amount)
        return True


class FincaTests(unittest.TestCase):
    def setUp(self):
        self.config = finca.load_config()
        self.state = finca.empty_state()
        self.purse = Purse()
        self.purse.bal[('simoncoin', 'tesoro_genesis')] = 5_000 * 100_000_000
        self.mark = finca.supply_fingerprint(self.purse.supply())
        self.now = 1_700_000_000

    def act(self, op, args=None, now=None, account=SECRET, present=True, purse=None, config=None):
        return finca.act(
            self.state, purse or self.purse, config or self.config, account, op, args or {},
            self.now if now is None else now, present=present,
        )

    def ripe(self, plot, crop_check=None):
        planted = self.act('plantar', {'plot': plot}, now=self.now)
        self.assertTrue(planted['ok'], planted.get('error'))
        self.now += 2 * reloj.REAL_SECONDS_PER_DAY + 5
        picked = self.act('cosechar', {'plot': plot}, now=self.now)
        self.assertTrue(picked['ok'], picked.get('error'))
        if crop_check:
            self.assertEqual(picked['view']['goods'][crop_check], picked['view']['goods'][crop_check])
        return picked

    def test_clock_matches_the_game_day(self):
        self.assertEqual(self.config['realSecondsPerGameDay'], reloj.REAL_SECONDS_PER_DAY)
        self.assertEqual(reloj.REAL_SECONDS_PER_DAY, 20 * 60)

    def test_cacao_sits_with_coffee_and_harvest_adds_kilos(self):
        plots = self.act('ver')['view']['plots']
        cafe = [row['id'] for row in plots if row['crop'] == 'cafe']
        cacao = [row['id'] for row in plots if row['crop'] == 'cacao']
        self.assertGreaterEqual(len(cafe), 1)
        self.assertGreaterEqual(len(cacao), 1)
        early = self.act('cosechar', {'plot': cacao[0]}, now=self.now + 10)
        self.assertFalse(early['ok'])
        self.ripe(cacao[0])
        self.assertEqual(self.state['harvestedKg']['cacao'], 90)
        self.assertEqual(self.state['accounts'][SECRET]['goods']['cacao_baba'], 1)
        self.assertEqual(self.state['harvestedKg']['cafe'], 0)
        chain = [row for row in self.state['publicEvents'] if row['kind'] == 'cosecha']
        self.assertEqual(chain[0]['prev'], '')
        self.assertEqual(chain[0]['hash'], finca._harvest_hash('cacao', 90, 90, ''))
        self.ripe(cafe[0])
        self.assertEqual(self.state['harvestedKg']['cafe'], 94)
        self.assertEqual(self.state['accounts'][SECRET]['goods']['cafe_cereza'], 1)
        self.assertEqual(self.state['harvestedKg']['cacao'], 90)

    def test_ten_cacao_harvests_make_two_bags_and_kilos_stay(self):
        plots = [row['id'] for row in self.act('ver')['view']['plots'] if row['crop'] == 'cacao']
        for index in range(10):
            self.ripe(plots[index % len(plots)])
        self.assertEqual(self.state['harvestedKg']['cacao'], 900)
        self.assertEqual(self.state['accounts'][SECRET]['goods']['cacao_baba'], 10)
        short = self.act('procesar', {'crop': 'cacao'}, now=self.now)
        self.assertTrue(short['ok'], short.get('error'))
        self.assertEqual(self.state['accounts'][SECRET]['goods']['cacao_baba'], 0)
        self.assertEqual(self.state['processedBags']['cacao'], 0)
        self.now += 8
        self.act('procesar', {'crop': 'cacao'}, now=self.now)
        self.now += 8
        done = self.act('ver', now=self.now)
        self.assertTrue(done['ok'])
        self.assertEqual(self.state['processedBags']['cacao'], 2)
        self.assertEqual(len(done['view']['bags']), 2)
        self.assertEqual(self.state['harvestedKg']['cacao'], 900)
        self.assertEqual(self.state['accounts'][SECRET]['goods'].get('cacao_baba', 0), 0)
        bags = [bag for bag in self.state['bags'].values() if bag['crop'] == 'cacao']
        self.assertEqual(sum(bag['kg'] for bag in bags), 300)
        self.assertTrue(all(bag['kg'] == 150 for bag in bags))
        self.assertEqual(sum(bag['freshKg'] for bag in bags), 900)
        self.assertEqual(len({bag['serial'] for bag in bags}), 2)
        self.assertTrue(all(bag['serial'].startswith('CAC-') for bag in bags))
        harvests = bags[0]['harvests']
        self.assertEqual(len(harvests), 10)
        again = finca._bag_hash(
            bags[0]['serial'], 'cacao', bags[0]['kg'], bags[0]['product'],
            harvests, bags[0]['batch'], bags[0]['stepHashes'], bags[0]['prev'],
        )
        self.assertEqual(again, bags[0]['hash'])
        self.assertEqual(again, bags[0]['chain'][0]['hash'])
        self.assertEqual(bags[1]['prev'], bags[0]['chain'][0]['hash'])
        feed = ' '.join(self.state['feed'])
        self.assertIn('Se procesó 1 cajón de cacao: 150 kg secos.', feed)
        self.assertNotIn(SECRET, feed)

    def test_sale_store_and_handoff_do_not_change_kilos_or_mint(self):
        plots = [row['id'] for row in self.act('ver')['view']['plots'] if row['crop'] == 'cacao']
        for index in range(10):
            self.ripe(plots[index % len(plots)])
        kg = self.state['harvestedKg']['cacao']
        self.act('procesar', {'crop': 'cacao'}, now=self.now)
        self.now += 8
        self.act('procesar', {'crop': 'cacao'}, now=self.now)
        self.now += 8
        self.act('ver', now=self.now)
        serials = [bag['serial'] for bag in self.state['bags'].values()]
        sold = self.act('vender', {'serial': serials[0], 'coin': 'simoncoin'}, now=self.now)
        self.assertTrue(sold['ok'], sold.get('error'))
        self.assertEqual(self.state['harvestedKg']['cacao'], kg)
        self.assertEqual(self.state['processedBags']['cacao'], 2)
        self.assertEqual(len(sold['view']['bags']), 1)
        stored = self.act('depositar', {'serial': serials[1]}, now=self.now)
        self.assertTrue(stored['ok'], stored.get('error'))
        self.assertEqual(len(stored['view']['bags']), 0)
        self.assertEqual(len(stored['view']['bank']), 1)
        self.assertEqual(self.state['harvestedKg']['cacao'], kg)
        back = self.act('retirar', {'serial': serials[1]}, now=self.now)
        self.assertTrue(back['ok'], back.get('error'))
        finca.handoff_bag(self.state, serials[1], SECRET, 'OtraCuenta', self.now)
        self.assertEqual(self.state['bags'][serials[1]]['owner'], 'OtraCuenta')
        self.assertEqual(self.state['harvestedKg']['cacao'], kg)
        self.assertEqual(self.state['processedBags']['cacao'], 2)
        self.assertEqual(finca.supply_fingerprint(self.purse.supply()), self.mark)
        self.assertEqual(self.purse.foundry['lingote_oro'], 4)
        self.assertEqual(self.purse.minted['simoncoin'], 100)

    def test_a_purse_that_mints_is_rejected(self):
        plots = [row['id'] for row in self.act('ver')['view']['plots'] if row['crop'] == 'cafe']
        for index in range(10):
            self.ripe(plots[index % len(plots)])
        self.act('procesar', {'crop': 'cafe'}, now=self.now)
        self.now += 8
        self.act('procesar', {'crop': 'cafe'}, now=self.now)
        self.now += 8
        self.act('procesar', {'crop': 'cafe'}, now=self.now)
        self.now += 8
        self.act('ver', now=self.now)
        serial = next(iter(self.state['bags']))
        greedy = GreedyPurse()
        greedy.bal[('simoncoin', 'casa_de_contratacion')] = 5_000 * 100_000_000
        sold = self.act('vender', {'serial': serial, 'coin': 'simoncoin'}, now=self.now, purse=greedy)
        self.assertFalse(sold['ok'])
        self.assertEqual(self.state['bags'][serial]['owner'], SECRET)
        self.assertEqual(self.state['bags'][serial]['place'], 'mochila')
        self.assertIn('no tiene monedas', sold['error'])

    def test_empty_fund_and_daily_cap(self):
        plots = [row['id'] for row in self.act('ver')['view']['plots'] if row['crop'] == 'cafe']
        for index in range(10):
            self.ripe(plots[index % len(plots)])
        self.act('procesar', {'crop': 'cafe'}, now=self.now)
        self.now += 8
        self.act('procesar', {'crop': 'cafe'}, now=self.now)
        self.now += 8
        self.act('procesar', {'crop': 'cafe'}, now=self.now)
        self.now += 8
        self.act('ver', now=self.now)
        serials = [bag['serial'] for bag in self.state['bags'].values()]
        dry = Purse()
        missed = self.act('vender', {'serial': serials[0], 'coin': 'simonplata'}, now=self.now, purse=dry)
        self.assertFalse(missed['ok'])
        self.assertEqual(self.state['bags'][serials[0]]['place'], 'mochila')
        cfg = json.loads(json.dumps(self.config))
        cfg['dailySellCapBags'] = 1
        first = self.act('vender', {'serial': serials[0], 'coin': 'simoncoin'}, now=self.now, config=cfg)
        self.assertTrue(first['ok'], first.get('error'))
        second = self.act('vender', {'serial': serials[1], 'coin': 'simoncoin'}, now=self.now, config=cfg)
        self.assertFalse(second['ok'])
        self.assertIn('tope', second['error'])
        self.assertEqual(finca.supply_fingerprint(self.purse.supply()), self.mark)

    def test_public_aggregate_hides_parties(self):
        self.ripe([row['id'] for row in self.act('ver')['view']['plots'] if row['crop'] == 'cacao'][0])
        public = finca.public_payload(self.state, self.purse, self.config)
        ledger = {
            'coins': [
                {'id': 'simoncoin', 'name': 'Simoncoin', 'minted': 1, 'max': 21_000_000},
                {'id': 'simonplata', 'name': 'Simonplata', 'minted': 0, 'max': 84_000_000},
                {'id': 'simonchis', 'name': 'Simonchis', 'minted': 0, 'max': 333_000_000},
            ],
            'foundry': {'lingote_oro': 4, 'lingote_plata': 1, 'lingote_cobre': 2},
        }
        body = finca.attach_public(ledger, self.state, self.purse, self.config)
        raw = json.dumps(body, ensure_ascii=False)
        self.assertNotIn(SECRET, raw)
        self.assertNotIn('counterparty', raw)
        self.assertNotIn('tesoro_genesis', raw)
        self.assertEqual(body['finca']['harvestedKg']['cacao'], 90)
        self.assertEqual(body['finca']['crops']['cafe']['sackKg'], 70)
        self.assertEqual(body['finca']['crops']['cacao']['sackKg'], 150)
        self.assertEqual(body['finca']['processedBags']['cafe'], 0)
        self.assertEqual(body['foundry']['lingote_oro'], 4)
        self.assertEqual(body['coins'][0]['max'], 21_000_000)
        self.assertNotIn('owner', json.dumps(public['events']))
        private = finca.private_payload(self.state)
        self.assertIn(SECRET, json.dumps(private))
        self.assertTrue(finca.can_see_private(finca.owner_email(), ''))
        self.assertTrue(finca.can_see_private('otra@example.com', 'compliance'))
        self.assertFalse(finca.can_see_private('otra@example.com', 'player'))

    def test_must_stand_at_the_farm(self):
        plots = self.act('ver')['view']['plots']
        away = self.act('plantar', {'plot': plots[0]['id']}, present=False)
        self.assertFalse(away['ok'])

    def test_state_roundtrip_keeps_kilos(self):
        self.ripe([row['id'] for row in self.act('ver')['view']['plots'] if row['crop'] == 'cacao'][0])
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, 'finca.json')
        finca.save(path, self.state)
        again = finca.load(path)
        self.assertEqual(again['harvestedKg']['cacao'], 90)
        self.assertNotIn(SECRET, json.dumps(finca.public_payload(again, self.purse, self.config)))

    def test_five_phases_keep_the_old_harvest_and_kilos(self):
        plot = {'crop': 'cacao', 'plantedAt': self.now}
        ripe = self.config['ripeAfterDays']
        day = reloj.REAL_SECONDS_PER_DAY
        seen = []
        for fraction in (0.1, 0.6, 1.1, 1.6, 2.1):
            moment = self.now + fraction * day
            phase = finca.phase_of(plot, moment, self.config)
            stage = finca.stage_of(plot, moment, self.config)
            seen.append(phase)
            self.assertEqual(phase == 'cosecha', stage == 'maduro')
            if fraction < ripe:
                self.assertNotEqual(stage, 'maduro')
        self.assertEqual(seen, ['siembra', 'crecimiento', 'floracion', 'fruto', 'cosecha'])
        plots = [row['id'] for row in self.act('ver')['view']['plots'] if row['crop'] == 'cacao']
        old = {'crop': 'cacao', 'stage': 'grown'}
        finca.migrate_plot(old, self.now, self.config)
        self.assertEqual(finca.phase_of(old, self.now, self.config), 'cosecha')
        self.assertEqual(finca.stage_of(old, self.now, self.config), 'maduro')
        planted = {'crop': 'cafe', 'stage': 'planted'}
        finca.migrate_plot(planted, self.now, self.config)
        self.assertEqual(finca.phase_of(planted, self.now, self.config), 'siembra')
        self.assertEqual(finca.legacy_phase('planted'), 'siembra')
        self.assertEqual(finca.legacy_phase('grown'), 'cosecha')
        self.assertEqual(finca.legacy_phase('growing'), 'crecimiento')
        self.assertEqual(finca.legacy_phase('flowering'), 'floracion')
        self.assertEqual(finca.legacy_phase('fruiting'), 'fruto')
        self.assertNotEqual(finca.stage_of(planted, self.now, self.config), 'maduro')
        empty = {'crop': 'cafe', 'stage': 'empty'}
        finca.migrate_plot(empty, self.now, self.config)
        self.assertEqual(empty.get('plantedAt', 0), 0)
        view = self.act('ver')['view']
        self.assertEqual(view['crops']['cafe']['steps'], ['Despulpar', 'Secar', 'Trillar'])
        self.assertEqual(view['crops']['cacao']['eduSteps'][-1], 'Kilos al Libro Mayor')
        self.assertIn('Fermentación', view['crops']['cafe']['eduSteps'])
        self.assertIn('70 kg', view['crops']['cafe']['note'])
        self.assertIn('450 kg', view['crops']['cacao']['note'])
        self.assertIn('32 semanas', view['ripeningNote'])
        kg = self.state['harvestedKg']['cacao']
        self.ripe(plots[0])
        self.assertEqual(self.state['harvestedKg']['cacao'], kg + 90)
        self.assertEqual(finca.supply_fingerprint(self.purse.supply()), self.mark)

    def test_real_units_do_not_create_kilos(self):
        cafe = finca.batch_balance(self.config['crops']['cafe'], self.config)
        self.assertEqual(cafe['freshKg'], 940)
        self.assertEqual(cafe['pergaminoKg'], 188)
        self.assertEqual(cafe['cargas'], 1)
        self.assertEqual(cafe['cargaRestoKg'], 63)
        self.assertEqual(cafe['dryKg'], 140)
        self.assertEqual(cafe['sackKg'], 70)
        cacao = finca.batch_balance(self.config['crops']['cacao'], self.config)
        self.assertEqual(cacao['freshKg'], 900)
        self.assertEqual(cacao['boxes'], 2)
        self.assertEqual(cacao['dryKg'], 300)
        self.assertEqual(cacao['sackKg'], 150)
        self.assertEqual(cacao['freshKg'], cacao['dryKg'] * 3)
        self.assertEqual(self.config['ripening']['weeksAfterFlower'], 32)
        self.assertEqual(self.config['ripening']['colorStages'], 8)
        self.assertEqual(self.config['crops']['cacao']['box']['babaKg'], 450)
        self.assertEqual(self.config['crops']['cafe']['parchment']['cargaKg'], 125)

    def test_legacy_bag_keeps_its_kilos(self):
        self.act('ver')
        self.state['harvestedKg']['cacao'] = 20
        self.state['harvestedKg']['cafe'] = 4
        self.state['bags']['CAC-viejo'] = {
            'serial': 'CAC-viejo', 'crop': 'cacao', 'kg': 50,
            'owner': SECRET, 'place': 'mochila', 'product': 'Cacao seco',
        }
        self.state['accounts'][SECRET]['batches']['cafe'] = {
            'id': 'lot-viejo', 'crop': 'cafe', 'step': 1, 'settled': True, 'readyAt': 0,
        }
        loaded = finca.normalize(self.state)
        self.assertEqual(loaded['harvestedKg']['cacao'], 20)
        self.assertEqual(loaded['harvestedKg']['cafe'], 4)
        self.assertEqual(loaded['bags']['CAC-viejo']['kg'], 50)
        self.assertEqual(loaded['bags']['CAC-viejo']['massRule'], 'legado')
        self.assertEqual(loaded['accounts'][SECRET]['batches']['cafe']['sackKg'], 70)
        self.assertEqual(loaded['accounts'][SECRET]['batches']['cafe']['massRule'], 'legado')
        before = finca.supply_fingerprint(self.purse.supply())
        self.assertEqual(finca.supply_fingerprint(self.purse.supply()), before)

    def test_guide_uses_short_sentences(self):
        with open(os.path.join(ROOT, 'play', 'instructivo.js'), encoding='utf-8') as handle:
            guide = handle.read()
        with open(os.path.join(ROOT, 'play', 'index.html'), encoding='utf-8') as handle:
            ayuda = handle.read()
        for line in (
            'Plantas en una parcela.',
            'Cosechas cuando está maduro.',
            'En el taller procesas el fruto.',
            'Vendes el bulto si la casa tiene monedas.',
        ):
            self.assertIn(line, guide)
            self.assertIn(line, ayuda)
        with open(os.path.join(ROOT, 'play', 'finca.js'), encoding='utf-8') as handle:
            panel = handle.read()
        self.assertIn('bulto de ${bag.kg || 0} kg', panel)
        self.assertIn('kg de café cereza', panel)
        self.assertIn('kg de cacao en baba', panel)
        self.assertIn('finca-carta', panel)
        self.assertIn('cereza_madura', panel)
        modelo = os.path.join(ROOT, 'play', 'finca-modelo.js')
        with open(modelo, encoding='utf-8') as handle:
            head = handle.read(40)
        self.assertFalse(head.lstrip().lower().startswith('<'))
        self.assertTrue(head.startswith('/*') or head.startswith('//') or head.startswith('(function'))
        with open(os.path.join(ROOT, 'play', 'finca-textos.json'), encoding='utf-8') as handle:
            cards = json.load(handle)
        self.assertEqual(cards['cafe'][3]['etapa'], 'cereza_madura')
        self.assertEqual(cards['cacao'][-1]['etapa'], 'kilos_libro_mayor')
        self.assertEqual(self.config['crops']['cafe']['kgPerHarvest'], 94)
        self.assertEqual(self.config['crops']['cacao']['kgPerHarvest'], 90)
        self.assertEqual(self.config['crops']['cafe']['bagKg'], 70)
        self.assertEqual(self.config['crops']['cacao']['bagKg'], 150)


if __name__ == '__main__':
    unittest.main()

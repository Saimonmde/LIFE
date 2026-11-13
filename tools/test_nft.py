# SPDX-License-Identifier: AGPL-3.0-or-later
"""Certificados SMC: firma, cadena, código único y tope de 21 millones."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economy as eco
import ed25519
import nft
import payout
import vault


class Ed25519Tests(unittest.TestCase):
    def test_rfc8032_empty_message(self):
        seed = bytes.fromhex('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60')
        pubkey = ed25519.publickey(seed)
        signature = ed25519.sign(b'', seed)
        self.assertEqual(pubkey.hex(), 'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a')
        self.assertEqual(signature.hex(), 'e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b')
        self.assertTrue(ed25519.verify(signature, b'', pubkey))
        self.assertFalse(ed25519.verify(signature, b'x', pubkey))


class CertificateTests(unittest.TestCase):
    def chain(self):
        seed = bytes(range(32))
        return {'seed': seed, 'chain': nft.empty_chain(ed25519.publickey(seed).hex())}

    def test_chain_signature_and_unique_codes(self):
        bag = self.chain()
        first = nft.issue(bag['chain'], bag['seed'], 'Ana', 4, 'fundidora', 'horno_cantera', now=10)
        second = nft.issue(bag['chain'], bag['seed'], 'Ana', 12, 'mina', 'cantera', now=20)
        self.assertNotEqual(first['code'], second['code'])
        self.assertTrue(first['code'].startswith('SMC-'))
        self.assertEqual(second['prev'], first['hash'])
        ok, message = nft.verify_chain(bag['chain'])
        self.assertTrue(ok, message)
        self.assertEqual(nft.metadata(bag['chain']['tokens'][0])['attributes'][0]['trait_type'], 'code')
        bag['chain']['tokens'][1]['amountSmh'] = 99
        bad, _why = nft.verify_chain(bag['chain'])
        self.assertFalse(bad)

    def test_token_sum_cannot_pass_the_cap(self):
        st = eco.empty_state()
        bag = self.chain()
        room = eco.MAX_SUPPLY - eco.TREASURY
        granted = eco.issue(st, 'Ana', eco.subunits(room + 5), 'tope', 'mint', now=1)
        self.assertEqual(granted, eco.subunits(room))
        token = nft.issue(bag['chain'], bag['seed'], 'Ana', granted, 'rio', '81,257', now=1)
        self.assertEqual(token['amountSmh'], eco.subunits(room))
        self.assertEqual(eco.issue(st, 'Ana', eco.subunits(1), 'de más', 'mint', now=2), 0)
        total = sum(item['amountSmh'] for item in bag['chain']['tokens'])
        self.assertLessEqual(total + eco.TREASURY_SMH, eco.MAX_SMH)
        ok, _message = nft.verify_chain(bag['chain'])
        self.assertTrue(ok)


class VaultAndPayoutTests(unittest.TestCase):
    def test_payout_adapter_refuses(self):
        self.assertFalse(payout.ADAPTER.enabled)
        with self.assertRaises(RuntimeError):
            payout.ADAPTER.payout('Ana', 10, 'USDT')

    def test_vault_survives_losing_the_carried_bag(self):
        state = vault.empty()
        box = vault.account(state, 'Ana')
        vault.add_smc(box, eco.subunits(8))
        vault.add_item(box, 'mineral_cobre', 3)
        carried = {'mineral_cobre': 5, 'mango': 1}
        carried.clear()
        self.assertEqual(carried, {})
        self.assertEqual(box['smcSubs'], eco.subunits(8))
        self.assertEqual(box['items']['mineral_cobre'], 3)


if __name__ == '__main__':
    unittest.main()

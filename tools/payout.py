# SPDX-License-Identifier: AGPL-3.0-or-later
"""Adaptador de pago real, apagado.

El turno de la cantera paga SaiMonCoins dentro del juego. Esta clase existe para
dejar escrito que no hay retiro a OnePay, USDT ni a ningún otro medio.
"""


class PayoutAdapter:
    name = 'OnePay/USDT'
    enabled = False

    def payout(self, player, amount, currency='USDT'):
        raise RuntimeError(
            'Los pagos reales están apagados. Las SMC no tienen valor y no se retiran por OnePay ni por USDT.'
        )


ADAPTER = PayoutAdapter()

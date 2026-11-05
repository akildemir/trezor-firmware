# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from apps.monero.signing.state import State
    from apps.monero.signing.step_07_all_outputs_set import _set_tx_extra
    from apps.monero.xmr import crypto, crypto_helpers


PAYMENT_ID_NONCE = b"\x02\x09\x01" + bytes(range(8))
ARBITRARY_DATA_NONCE = b"\x02\x03abc"


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroTxExtra(unittest.TestCase):
    """
    tx.extra is laid out as TX_EXTRA_TAG_PUBKEY, the payment id nonce, then
    the arbitrary data nonce. Monero's find_tx_extra_field_by_type picks the
    first nonce as the payment id, so the order matters.
    """

    def setUp(self):
        self.state = State()
        self.state.tx_priv = crypto.random_scalar()
        self.state.tx_pub = crypto.scalarmult_base_into(None, self.state.tx_priv)
        self.pubkey_entry = b"\x01" + crypto_helpers.encodepoint(self.state.tx_pub)

    def test_pubkey_only(self):
        self.assertEqual(_set_tx_extra(self.state), self.pubkey_entry)

    def test_arbitrary_data_follows_payment_id(self):
        self.state.extra_nonce = PAYMENT_ID_NONCE
        self.state.extra_arbitrary_data = ARBITRARY_DATA_NONCE
        self.assertEqual(
            _set_tx_extra(self.state),
            self.pubkey_entry + PAYMENT_ID_NONCE + ARBITRARY_DATA_NONCE,
        )
        # both buffers are consumed so nothing can write them twice
        self.assertIsNone(self.state.extra_nonce)
        self.assertIsNone(self.state.extra_arbitrary_data)

    def test_arbitrary_data_without_payment_id(self):
        self.state.extra_arbitrary_data = ARBITRARY_DATA_NONCE
        self.assertEqual(
            _set_tx_extra(self.state), self.pubkey_entry + ARBITRARY_DATA_NONCE
        )

    def test_payment_id_without_arbitrary_data(self):
        self.state.extra_nonce = PAYMENT_ID_NONCE
        self.assertEqual(
            _set_tx_extra(self.state), self.pubkey_entry + PAYMENT_ID_NONCE
        )


if __name__ == "__main__":
    unittest.main()

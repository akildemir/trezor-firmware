# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.BITCOIN_ONLY:
    from trezor.messages import (
        MoneroAccountPublicAddress,
        MoneroTransactionData,
        MoneroTransactionDestinationEntry,
    )

    from apps.monero.signing import step_01_init_transaction
    from apps.monero.signing.state import State


def _dst(tag: int, amount: int) -> "MoneroTransactionDestinationEntry":
    return MoneroTransactionDestinationEntry(
        amount=amount,
        addr=MoneroAccountPublicAddress(
            spend_public_key=bytes([tag]) * 32,
            view_public_key=bytes([tag + 1]) * 32,
        ),
        is_subaddress=False,
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroCheckPaymentId(unittest.TestCase):
    """
    A payment id that cannot go into a transaction must be rejected before the
    confirmation dialog renders it into an integrated address -- encode_addr
    appends whatever length it is given.
    """

    def _check(self, payment_id, integrated_indices):
        change = _dst(20, 500)
        tsx_data = MoneroTransactionData(
            outputs=[_dst(10, 100), change],
            change_dts=change,
            fee=1000,
            payment_id=payment_id,
            integrated_indices=integrated_indices,
        )
        step_01_init_transaction._check_payment_id(tsx_data)

    def test_wrong_length_is_rejected(self):
        with self.assertRaises(ValueError):
            self._check(b"\x01\x02\x03\x04\x05", [])

    def test_long_payment_id_cannot_be_integrated(self):
        # there is no 32-byte integrated address
        with self.assertRaises(ValueError):
            self._check(bytes(range(32)), [0])

    def test_short_payment_id_can_be_integrated(self):
        self._check(bytes(range(8)), [0])

    def test_short_payment_id_without_indices(self):
        self._check(bytes(range(8)), [])

    def test_long_payment_id_without_indices(self):
        # 32 bytes is the plaintext form
        self._check(bytes(range(32)), [])

    def test_no_payment_id(self):
        self._check(None, [])

    def test_empty_payment_id(self):
        # the client may send the field as empty bytes rather than omitting it;
        # _process_payment_id writes nothing for it, so it must not be rejected
        self._check(b"", [])

    def test_empty_payment_id_with_indices(self):
        self._check(b"", [0])


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroArbitraryData(unittest.TestCase):
    """
    Host-provided arbitrary data lands in tx.extra as a second TX_EXTRA_NONCE
    entry next to the payment id one, so it obeys the same 255-byte cap and
    is rejected before the confirmation displays it.
    """

    def _tsx_data(self, arbitrary_data):
        change = _dst(20, 500)
        return MoneroTransactionData(
            outputs=[_dst(10, 100), change],
            change_dts=change,
            fee=1000,
            arbitrary_data=arbitrary_data,
        )

    def _process(self, arbitrary_data):
        state = State()
        tsx_data = self._tsx_data(arbitrary_data)
        step_01_init_transaction._check_arbitrary_data(tsx_data)
        step_01_init_transaction._process_arbitrary_data(state, tsx_data)
        return state.extra_arbitrary_data

    def test_data_is_wrapped_in_a_nonce_entry(self):
        # TX_EXTRA_NONCE tag, one length byte, then the data without a sub-tag
        self.assertEqual(
            self._process(b"\xde\xad\xbe\xef"), b"\x02\x04\xde\xad\xbe\xef"
        )

    def test_max_length_is_accepted(self):
        data = bytes(range(256))[:255]
        self.assertEqual(self._process(data), b"\x02\xff" + data)

    def test_oversized_data_is_rejected_before_confirmation(self):
        with self.assertRaises(ValueError):
            step_01_init_transaction._check_arbitrary_data(self._tsx_data(bytes(256)))

    def test_oversized_data_is_rejected_when_processed(self):
        with self.assertRaises(ValueError):
            step_01_init_transaction._process_arbitrary_data(
                State(), self._tsx_data(bytes(256))
            )

    def test_no_data_writes_nothing(self):
        self.assertIsNone(self._process(None))

    def test_empty_data_writes_nothing(self):
        # the client may send the field as empty bytes rather than omitting it
        self.assertIsNone(self._process(b""))


if __name__ == "__main__":
    unittest.main()

import asyncio
from typing import Optional

from blspy import G2Element

from cryptodogelight.types.coin_record import CoinRecord
from cryptodogelight.types.coin_spend import CoinSpend
from cryptodogelight.types.spend_bundle import SpendBundle
from cryptodogelight.util.config import load_config, save_config
import logging

import pytest

from cryptodogelight.consensus.block_rewards import calculate_base_farmer_reward, calculate_pool_reward
from cryptodogelight.rpc.full_node_rpc_api import FullNodeRpcApi
from cryptodogelight.rpc.full_node_rpc_client import FullNodeRpcClient
from cryptodogelight.rpc.rpc_server import start_rpc_server
from cryptodogelight.rpc.wallet_rpc_api import WalletRpcApi
from cryptodogelight.rpc.wallet_rpc_client import WalletRpcClient
from cryptodogelight.simulator.simulator_protocol import FarmNewBlockProtocol
from cryptodogelight.types.peer_info import PeerInfo
from cryptodogelight.util.bech32m import encode_puzzle_hash
from cryptodogelight.consensus.coinbase import create_puzzlehash_for_pk
from cryptodogelight.wallet.derive_keys import master_sk_to_wallet_sk
from cryptodogelight.util.ints import uint16, uint32
from cryptodogelight.wallet.transaction_record import TransactionRecord
from tests.setup_nodes import bt, setup_simulators_and_wallets, self_hostname
from tests.time_out_assert import time_out_assert

log = logging.getLogger(__name__)


class TestWalletRpc:
    @pytest.fixture(scope="function")
    async def two_wallet_nodes(self):
        async for _ in setup_simulators_and_wallets(1, 2, {}):
            yield _

    @pytest.mark.parametrize(
        "trusted",
        [True, False],
    )
    @pytest.mark.asyncio
    async def test_wallet_rpc(self, two_wallet_nodes, trusted):
        test_rpc_port = uint16(21529)
        test_rpc_port_2 = uint16(21536)
        test_rpc_port_node = uint16(21530)
        num_blocks = 5
        full_nodes, wallets = two_wallet_nodes
        full_node_api = full_nodes[0]
        full_node_server = full_node_api.full_node.server
        wallet_node, server_2 = wallets[0]
        wallet_node_2, server_3 = wallets[1]
        wallet = wallet_node.wallet_state_manager.main_wallet
        wallet_2 = wallet_node_2.wallet_state_manager.main_wallet
        ph = await wallet.get_new_puzzlehash()
        ph_2 = await wallet_2.get_new_puzzlehash()

        await server_2.start_client(PeerInfo("localhost", uint16(full_node_server._port)), None)
        await server_3.start_client(PeerInfo("localhost", uint16(full_node_server._port)), None)

        if trusted:
            wallet_node.config["trusted_peers"] = {full_node_server.node_id: full_node_server.node_id}
            wallet_node_2.config["trusted_peers"] = {full_node_server.node_id: full_node_server.node_id}
        else:
            wallet_node.config["trusted_peers"] = {}
            wallet_node_2.config["trusted_peers"] = {}

        for i in range(0, num_blocks):
            await full_node_api.farm_new_transaction_block(FarmNewBlockProtocol(ph))

        initial_funds = sum(
            [calculate_pool_reward(uint32(i)) + calculate_base_farmer_reward(uint32(i)) for i in range(1, num_blocks)]
        )
        initial_funds_eventually = sum(
            [
                calculate_pool_reward(uint32(i)) + calculate_base_farmer_reward(uint32(i))
                for i in range(1, num_blocks + 1)
            ]
        )

        wallet_rpc_api = WalletRpcApi(wallet_node)
        wallet_rpc_api_2 = WalletRpcApi(wallet_node_2)

        config = bt.config
        hostname = config["self_hostname"]
        daemon_port = config["daemon_port"]

        def stop_node_cb():
            pass

        full_node_rpc_api = FullNodeRpcApi(full_node_api.full_node)

        rpc_cleanup_node = await start_rpc_server(
            full_node_rpc_api,
            hostname,
            daemon_port,
            test_rpc_port_node,
            stop_node_cb,
            bt.root_path,
            config,
            connect_to_daemon=False,
        )
        rpc_cleanup = await start_rpc_server(
            wallet_rpc_api,
            hostname,
            daemon_port,
            test_rpc_port,
            stop_node_cb,
            bt.root_path,
            config,
            connect_to_daemon=False,
        )
        rpc_cleanup_2 = await start_rpc_server(
            wallet_rpc_api_2,
            hostname,
            daemon_port,
            test_rpc_port_2,
            stop_node_cb,
            bt.root_path,
            config,
            connect_to_daemon=False,
        )

        await time_out_assert(5, wallet.get_confirmed_balance, initial_funds)
        await time_out_assert(5, wallet.get_unconfirmed_balance, initial_funds)

        client = await WalletRpcClient.create(self_hostname, test_rpc_port, bt.root_path, config)
        client_2 = await WalletRpcClient.create(self_hostname, test_rpc_port_2, bt.root_path, config)
        client_node = await FullNodeRpcClient.create(self_hostname, test_rpc_port_node, bt.root_path, config)
        try:
            await time_out_assert(5, client.get_synced)
            addr = encode_puzzle_hash(await wallet_node_2.wallet_state_manager.main_wallet.get_new_puzzlehash(), "xcd")
            tx_amount = 15600000
            try:
                await client.send_transaction("1", 100000000000000001, addr)
                raise Exception("Should not create high value tx")
            except ValueError:
                pass

            # Tests sending a basic transaction
            tx = await client.send_transaction("1", tx_amount, addr, memos=["this is a basic tx"])
            transaction_id = tx.name

            async def tx_in_mempool():
                tx = await client.get_transaction("1", transaction_id)
                return tx.is_in_mempool()

            await time_out_assert(5, tx_in_mempool, True)
            await time_out_assert(5, wallet.get_unconfirmed_balance, initial_funds - tx_amount)
            assert (await client.get_wallet_balance("1"))["unconfirmed_wallet_balance"] == initial_funds - tx_amount
            assert (await client.get_wallet_balance("1"))["confirmed_wallet_balance"] == initial_funds

            for i in range(0, 5):
                await full_node_api.farm_new_transaction_block(FarmNewBlockProtocol(ph_2))

            async def eventual_balance():
                return (await client.get_wallet_balance("1"))["confirmed_wallet_balance"]

            # Checks that the memo can be retrieved
            tx_confirmed = await client.get_transaction("1", transaction_id)
            assert tx_confirmed.confirmed
            assert len(tx_confirmed.get_memos()) == 1
            assert [b"this is a basic tx"] in tx_confirmed.get_memos().values()
            assert list(tx_confirmed.get_memos().keys())[0] in [a.name() for a in tx.spend_bundle.additions()]

            await time_out_assert(5, eventual_balance, initial_funds_eventually - tx_amount)

            # Tests offline signing
            ph_3 = await wallet_node_2.wallet_state_manager.main_wallet.get_new_puzzlehash()
            ph_4 = await wallet_node_2.wallet_state_manager.main_wallet.get_new_puzzlehash()
            ph_5 = await wallet_node_2.wallet_state_manager.main_wallet.get_new_puzzlehash()

            # Test basic transaction to one output
            signed_tx_amount = 888000
            tx_res: TransactionRecord = await client.create_signed_transaction(
                [{"amount": signed_tx_amount, "puzzle_hash": ph_3, "memos": ["My memo"]}]
            )

            assert tx_res.fee_amount == 0
            assert tx_res.amount == signed_tx_amount
            assert len(tx_res.additions) == 2  # The output and the change
            assert any([addition.amount == signed_tx_amount for addition in tx_res.additions])

            push_res = await client_node.push_tx(tx_res.spend_bundle)
            assert push_res["success"]
            assert (await client.get_wallet_balance("1"))[
                "confirmed_wallet_balance"
            ] == initial_funds_eventually - tx_amount

            for i in range(0, 5):
                await client.farm_block(encode_puzzle_hash(ph_2, "xcd"))
                await asyncio.sleep(0.5)

            await time_out_assert(5, eventual_balance, initial_funds_eventually - tx_amount - signed_tx_amount)

            # Test transaction to two outputs, from a specified coin, with a fee
            coin_to_spend = None
            for addition in tx_res.additions:
                if addition.amount != signed_tx_amount:
                    coin_to_spend = addition
            assert coin_to_spend is not None

            tx_res = await client.create_signed_transaction(
                [{"amount": 444, "puzzle_hash": ph_4, "memos": ["hhh"]}, {"amount": 999, "puzzle_hash": ph_5}],
                coins=[coin_to_spend],
                fee=100,
            )
            assert tx_res.fee_amount == 100
            assert tx_res.amount == 444 + 999
            assert len(tx_res.additions) == 3  # The outputs and the change
            assert any([addition.amount == 444 for addition in tx_res.additions])
            assert any([addition.amount == 999 for addition in tx_res.additions])
            assert sum([rem.amount for rem in tx_res.removals]) - sum([ad.amount for ad in tx_res.additions]) == 100

            push_res = await client_node.push_tx(tx_res.spend_bundle)
            assert push_res["success"]
            for i in range(0, 5):
                await client.farm_block(encode_puzzle_hash(ph_2, "xcd"))
                await asyncio.sleep(0.5)

            found: bool = False
            for addition in tx_res.spend_bundle.additions():
                if addition.amount == 444:
                    cr: Optional[CoinRecord] = await client_node.get_coin_record_by_name(addition.name())
                    assert cr is not None
                    spend: CoinSpend = await client_node.get_puzzle_and_solution(
                        addition.parent_coin_info, cr.confirmed_block_index
                    )
                    sb: SpendBundle = SpendBundle([spend], G2Element())
                    assert sb.get_memos() == {addition.name(): [b"hhh"]}
                    found = True
            assert found

            new_balance = initial_funds_eventually - tx_amount - signed_tx_amount - 444 - 999 - 100
            await time_out_assert(5, eventual_balance, new_balance)

            send_tx_res: TransactionRecord = await client.send_transaction_multi(
                "1",
                [
                    {"amount": 555, "puzzle_hash": ph_4, "memos": ["FiMemo"]},
                    {"amount": 666, "puzzle_hash": ph_5, "memos": ["SeMemo"]},
                ],
                fee=200,
            )
            assert send_tx_res is not None
            assert send_tx_res.fee_amount == 200
            assert send_tx_res.amount == 555 + 666
            assert len(send_tx_res.additions) == 3  # The outputs and the change
            assert any([addition.amount == 555 for addition in send_tx_res.additions])
            assert any([addition.amount == 666 for addition in send_tx_res.additions])
            assert (
                sum([rem.amount for rem in send_tx_res.removals]) - sum([ad.amount for ad in send_tx_res.additions])
                == 200
            )

            await asyncio.sleep(3)
            for i in range(0, 5):
                await client.farm_block(encode_puzzle_hash(ph_2, "xcd"))
                await asyncio.sleep(0.5)

            new_balance = new_balance - 555 - 666 - 200
            await time_out_assert(5, eventual_balance, new_balance)

            # Checks that the memo can be retrieved
            tx_confirmed = await client.get_transaction("1", send_tx_res.name)
            assert tx_confirmed.confirmed
            assert len(tx_confirmed.get_memos()) == 2
            print(tx_confirmed.get_memos())
            assert [b"FiMemo"] in tx_confirmed.get_memos().values()
            assert [b"SeMemo"] in tx_confirmed.get_memos().values()
            assert list(tx_confirmed.get_memos().keys())[0] in [a.name() for a in send_tx_res.spend_bundle.additions()]
            assert list(tx_confirmed.get_memos().keys())[1] in [a.name() for a in send_tx_res.spend_bundle.additions()]

            ##############
            # CATS       #
            ##############

            # Creates a wallet and a CAT with 20 mojos
            res = await client.create_new_cat_and_wallet(20)
            assert res["success"]
            cat_0_id = res["wallet_id"]
            colour = bytes.fromhex(res["colour"])
            assert len(colour) > 0

            bal_0 = await client.get_wallet_balance(cat_0_id)
            assert bal_0["confirmed_wallet_balance"] == 0
            assert bal_0["pending_coin_removal_count"] == 1
            col = await client.get_cat_colour(cat_0_id)
            assert col == colour
            assert (await client.get_cat_name(cat_0_id)) == "CAT Wallet"
            await client.set_cat_name(cat_0_id, "My cat")
            assert (await client.get_cat_name(cat_0_id)) == "My cat"

            await asyncio.sleep(1)
            for i in range(0, 5):
                await client.farm_block(encode_puzzle_hash(ph_2, "xcd"))
                await asyncio.sleep(0.5)

            bal_0 = await client.get_wallet_balance(cat_0_id)
            assert bal_0["confirmed_wallet_balance"] == 20
            assert bal_0["pending_coin_removal_count"] == 0
            assert bal_0["unspent_coin_count"] == 1

            # Creates a second wallet with the same CAT
            res = await client_2.create_wallet_for_existing_cat(colour)
            assert res["success"]
            cat_1_id = res["wallet_id"]
            colour_1 = bytes.fromhex(res["colour"])
            assert colour_1 == colour

            await asyncio.sleep(1)
            for i in range(0, 5):
                await client.farm_block(encode_puzzle_hash(ph_2, "xcd"))
                await asyncio.sleep(0.5)
            bal_1 = await client_2.get_wallet_balance(cat_1_id)
            assert bal_1["confirmed_wallet_balance"] == 0

            addr_0 = await client.get_next_address(cat_0_id, False)
            addr_1 = await client_2.get_next_address(cat_1_id, False)

            assert addr_0 != addr_1

            await client.cat_spend(cat_0_id, 4, addr_1, 0, ["the cat memo"])

            await asyncio.sleep(1)
            for i in range(0, 5):
                await client.farm_block(encode_puzzle_hash(ph_2, "xcd"))
                await asyncio.sleep(0.5)

            bal_0 = await client.get_wallet_balance(cat_0_id)
            bal_1 = await client_2.get_wallet_balance(cat_1_id)

            assert bal_0["confirmed_wallet_balance"] == 16
            assert bal_1["confirmed_wallet_balance"] == 4

            # Keys and addresses

            address = await client.get_next_address("1", True)
            assert len(address) > 10

            all_transactions = await client.get_transactions("1")
            some_transactions = await client.get_transactions("1", 0, 5)
            some_transactions_2 = await client.get_transactions("1", 5, 10)
            assert len(all_transactions) > 1
            assert some_transactions == all_transactions[len(all_transactions)-5:len(all_transactions)]
            assert some_transactions_2 == all_transactions[len(all_transactions)-10:len(all_transactions)-5]

            transaction_count = await client.get_transaction_count("1")
            assert transaction_count == len(all_transactions)

            pks = await client.get_public_keys()
            assert len(pks) == 1

            assert (await client.get_height_info()) > 0

            created_tx = await client.send_transaction("1", tx_amount, addr)

            async def tx_in_mempool_2():
                tx = await client.get_transaction("1", created_tx.name)
                return tx.is_in_mempool()

            await time_out_assert(5, tx_in_mempool_2, True)
            assert len(await wallet.wallet_state_manager.tx_store.get_unconfirmed_for_wallet(1)) == 1
            await client.delete_unconfirmed_transactions("1")
            assert len(await wallet.wallet_state_manager.tx_store.get_unconfirmed_for_wallet(1)) == 0

            sk_dict = await client.get_private_key(pks[0])
            assert sk_dict["fingerprint"] == pks[0]
            assert sk_dict["sk"] is not None
            assert sk_dict["pk"] is not None
            assert sk_dict["seed"] is not None

            mnemonic = await client.generate_mnemonic()
            assert len(mnemonic) == 24

            await client.add_key(mnemonic)

            pks = await client.get_public_keys()
            assert len(pks) == 2

            await client.log_in_and_skip(pks[1])
            sk_dict = await client.get_private_key(pks[1])
            assert sk_dict["fingerprint"] == pks[1]

            # Add in reward addresses into farmer and pool for testing delete key checks
            # set farmer to first private key
            sk = await wallet_node.get_key_for_fingerprint(pks[0])
            test_ph = create_puzzlehash_for_pk(master_sk_to_wallet_sk(sk, uint32(0)).get_g1())
            test_config = load_config(wallet_node.root_path, "config.yaml")
            test_config["farmer"]["xcd_target_address"] = encode_puzzle_hash(test_ph, "txcd")
            # set pool to second private key
            sk = await wallet_node.get_key_for_fingerprint(pks[1])
            test_ph = create_puzzlehash_for_pk(master_sk_to_wallet_sk(sk, uint32(0)).get_g1())
            test_config["pool"]["xcd_target_address"] = encode_puzzle_hash(test_ph, "txcd")
            save_config(wallet_node.root_path, "config.yaml", test_config)

            # Check first key
            sk_dict = await client.check_delete_key(pks[0])
            assert sk_dict["fingerprint"] == pks[0]
            assert sk_dict["used_for_farmer_rewards"] is True
            assert sk_dict["used_for_pool_rewards"] is False

            # Check second key
            sk_dict = await client.check_delete_key(pks[1])
            assert sk_dict["fingerprint"] == pks[1]
            assert sk_dict["used_for_farmer_rewards"] is False
            assert sk_dict["used_for_pool_rewards"] is True

            # Check unknown key
            sk_dict = await client.check_delete_key(123456)
            assert sk_dict["fingerprint"] == 123456
            assert sk_dict["used_for_farmer_rewards"] is False
            assert sk_dict["used_for_pool_rewards"] is False

            await client.delete_key(pks[0])
            await client.log_in_and_skip(pks[1])
            assert len(await client.get_public_keys()) == 1

            assert not (await client.get_sync_status())

            wallets = await client.get_wallets()
            assert len(wallets) == 1
            balance = await client.get_wallet_balance(wallets[0]["id"])
            assert balance["unconfirmed_wallet_balance"] == 0

            try:
                await client.send_transaction(wallets[0]["id"], 100, addr)
                raise Exception("Should not create tx if no balance")
            except ValueError:
                pass
            # Delete all keys
            await client.delete_all_keys()
            assert len(await client.get_public_keys()) == 0
        finally:
            # Checks that the RPC manages to stop the node
            client.close()
            client_2.close()
            client_node.close()
            await client.await_closed()
            await client_2.await_closed()
            await client_node.await_closed()
            await rpc_cleanup()
            await rpc_cleanup_2()
            await rpc_cleanup_node()

import dataclasses
import warnings

from dataclasses import dataclass
from typing import List, Dict

from blspy import AugSchemeMPL, G2Element
from clvm.casts import int_from_bytes

from cryptodogelight.consensus.default_constants import DEFAULT_CONSTANTS
from cryptodogelight.types.blockchain_format.coin import Coin
from cryptodogelight.types.blockchain_format.sized_bytes import bytes32
from cryptodogelight.util.streamable import Streamable, dataclass_from_dict, recurse_jsonify, streamable
from cryptodogelight.wallet.util.debug_spend_bundle import debug_spend_bundle
from .blockchain_format.program import Program

from .coin_spend import CoinSpend
from .condition_opcodes import ConditionOpcode


@dataclass(frozen=True)
@streamable
class SpendBundle(Streamable):
    """
    This is a list of coins being spent along with their solution programs, and a single
    aggregated signature. This is the object that most closely corresponds to a bitcoin
    transaction (although because of non-interactive signature aggregation, the boundaries
    between transactions are more flexible than in bitcoin).
    """

    coin_spends: List[CoinSpend]
    aggregated_signature: G2Element

    @property
    def coin_solutions(self):
        return self.coin_spends

    @classmethod
    def aggregate(cls, spend_bundles) -> "SpendBundle":
        coin_spends: List[CoinSpend] = []
        sigs: List[G2Element] = []
        for bundle in spend_bundles:
            coin_spends += bundle.coin_spends
            sigs.append(bundle.aggregated_signature)
        aggregated_signature = AugSchemeMPL.aggregate(sigs)
        return cls(coin_spends, aggregated_signature)

    def additions(self) -> List[Coin]:
        items: List[Coin] = []
        for coin_spend in self.coin_spends:
            items.extend(coin_spend.additions())
        return items

    def removals(self) -> List[Coin]:
        """This should be used only by wallet"""
        return [_.coin for _ in self.coin_spends]

    def fees(self) -> int:
        """Unsafe to use for fees validation!!!"""
        amount_in = sum(_.amount for _ in self.removals())
        amount_out = sum(_.amount for _ in self.additions())

        return amount_in - amount_out

    def name(self) -> bytes32:
        return self.get_hash()

    def debug(self, agg_sig_additional_data=DEFAULT_CONSTANTS.AGG_SIG_ME_ADDITIONAL_DATA):
        debug_spend_bundle(self, agg_sig_additional_data)

    def not_ephemeral_additions(self):
        all_removals = self.removals()
        all_additions = self.additions()
        result: List[Coin] = []

        for add in all_additions:
            if add in all_removals:
                continue
            result.append(add)

        return result

    def get_memos(self) -> Dict[bytes32, List[bytes]]:
        """
        Retrieves the memos for additions in this spend_bundle, which are formatted as a list in the 3rd parameter of
        CREATE_COIN. If there are no memos, the addition coin_id is not included. If they are not formatted as a list
        of bytes, they are not included. This is expensive to call, it should not be used in full node code.
        """
        memos: Dict[bytes32, List[bytes]] = {}
        for coin_spend in self.coin_spends:
            result = Program.from_bytes(bytes(coin_spend.puzzle_reveal)).run(
                Program.from_bytes(bytes(coin_spend.solution))
            )
            for condition in result.as_python():
                if condition[0] == ConditionOpcode.CREATE_COIN and len(condition) >= 4:
                    # If only 3 elements (opcode + 2 args), there is no memo, this is ph, amount
                    coin_added = Coin(coin_spend.coin.name(), bytes32(condition[1]), int_from_bytes(condition[2]))
                    if type(condition[3]) != list:
                        # If it's not a list, it's not the correct format
                        continue
                    memos[coin_added.name()] = condition[3]
        return memos

    # Note that `coin_spends` used to have the bad name `coin_solutions`.
    # Some API still expects this name. For now, we accept both names.
    #
    # TODO: continue this deprecation. Eventually, all code below here should be removed.
    #  1. set `exclude_modern_keys` to `False` (and manually set to `True` where necessary)
    #  2. set `include_legacy_keys` to `False` (and manually set to `False` where necessary)
    #  3. remove all references to `include_legacy_keys=True`
    #  4. remove all code below this point

    @classmethod
    def from_json_dict(cls, json_dict):
        if "coin_solutions" in json_dict:
            if "coin_spends" not in json_dict:
                json_dict = dict(
                    aggregated_signature=json_dict["aggregated_signature"], coin_spends=json_dict["coin_solutions"]
                )
                warnings.warn("`coin_solutions` is now `coin_spends` in `SpendBundle.from_json_dict`")
            else:
                raise ValueError("JSON contains both `coin_solutions` and `coin_spends`, just use `coin_spends`")
        return dataclass_from_dict(cls, json_dict)

    def to_json_dict(self, include_legacy_keys: bool = True, exclude_modern_keys: bool = True):
        if include_legacy_keys is False and exclude_modern_keys is True:
            raise ValueError("`coin_spends` not included in legacy or modern outputs")
        d = dataclasses.asdict(self)
        if include_legacy_keys:
            d["coin_solutions"] = d["coin_spends"]
        if exclude_modern_keys:
            del d["coin_spends"]
        return recurse_jsonify(d)

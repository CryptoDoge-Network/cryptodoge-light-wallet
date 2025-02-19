from typing import Dict, Optional, Tuple

from cryptodogelight.types.blockchain_format.program import Program, INFINITE_COST
from cryptodogelight.types.condition_opcodes import ConditionOpcode
from cryptodogelight.types.spend_bundle import SpendBundle
from cryptodogelight.util.condition_tools import conditions_dict_for_solution
from cryptodogelight.wallet.cc_wallet import cc_utils
from cryptodogelight.wallet.trade_record import TradeRecord
from cryptodogelight.wallet.trading.trade_status import TradeStatus


def trade_status_ui_string(status: TradeStatus):
    if status is TradeStatus.PENDING_CONFIRM:
        return "Pending Confirmation"
    elif status is TradeStatus.CANCELED:
        return "Canceled"
    elif status is TradeStatus.CONFIRMED:
        return "Confirmed"
    elif status is TradeStatus.PENDING_CANCEL:
        return "Pending Cancellation"
    elif status is TradeStatus.FAILED:
        return "Failed"
    elif status is TradeStatus.PENDING_ACCEPT:
        return "Pending"


def trade_record_to_dict(record: TradeRecord) -> Dict:
    """Convenience function to return only part of trade record we care about and show correct status to the ui"""
    result = {}
    result["trade_id"] = record.trade_id.hex()
    result["sent"] = record.sent
    result["my_offer"] = record.my_offer
    result["created_at_time"] = record.created_at_time
    result["accepted_at_time"] = record.accepted_at_time
    result["confirmed_at_index"] = record.confirmed_at_index
    result["status"] = trade_status_ui_string(TradeStatus(record.status))
    success, offer_dict, error = get_discrepancies_for_spend_bundle(record.spend_bundle)
    if success is False or offer_dict is None:
        raise ValueError(error)
    result["offer_dict"] = offer_dict
    return result


# Returns the relative difference in value between the amount outputted by a puzzle and solution and a coin's amount
def get_output_discrepancy_for_puzzle_and_solution(coin, puzzle, solution):
    discrepancy = coin.amount - get_output_amount_for_puzzle_and_solution(puzzle, solution)
    return discrepancy

    # Returns the amount of value outputted by a puzzle and solution


def get_output_amount_for_puzzle_and_solution(puzzle: Program, solution: Program) -> int:
    error, conditions, cost = conditions_dict_for_solution(puzzle, solution, INFINITE_COST)
    total = 0
    if conditions:
        for _ in conditions.get(ConditionOpcode.CREATE_COIN, []):
            total += Program.to(_.vars[1]).as_int()
    return total


def get_discrepancies_for_spend_bundle(
    trade_offer: SpendBundle,
) -> Tuple[bool, Optional[Dict], Optional[Exception]]:
    try:
        cc_discrepancies: Dict[str, int] = dict()
        for coinsol in trade_offer.coin_spends:
            puzzle: Program = Program.from_bytes(bytes(coinsol.puzzle_reveal))
            solution: Program = Program.from_bytes(bytes(coinsol.solution))
            # work out the deficits between coin amount and expected output for each
            matched, curried_args = cc_utils.match_cat_puzzle(puzzle)
            if matched:
                # Calculate output amounts
                mod_hash, genesis_checker_hash, inner_puzzle = curried_args
                innersol = solution.first()

                total = get_output_amount_for_puzzle_and_solution(inner_puzzle, innersol)
                colour = bytes(genesis_checker_hash).hex()
                if colour in cc_discrepancies:
                    cc_discrepancies[colour] += coinsol.coin.amount - total
                else:
                    cc_discrepancies[colour] = coinsol.coin.amount - total
            else:
                coin_amount = coinsol.coin.amount
                out_amount = get_output_amount_for_puzzle_and_solution(puzzle, solution)
                diff = coin_amount - out_amount
                if "cryptodogelight" in cc_discrepancies:
                    cc_discrepancies["cryptodogelight"] = cc_discrepancies["cryptodogelight"] + diff
                else:
                    cc_discrepancies["cryptodogelight"] = diff

        return True, cc_discrepancies, None
    except Exception as e:
        return False, None, e

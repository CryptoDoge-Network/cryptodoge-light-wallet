from dataclasses import dataclass
from typing import Optional

from cryptodogelight.types.blockchain_format.sized_bytes import bytes32
from cryptodogelight.types.blockchain_format.program import Program
from cryptodogelight.util.ints import uint64
from cryptodogelight.util.streamable import Streamable, streamable


@dataclass(frozen=True)
@streamable
class LineageProof(Streamable):
    parent_name: Optional[bytes32] = None
    inner_puzzle_hash: Optional[bytes32] = None
    amount: Optional[uint64] = None

    def to_program(self) -> Program:
        final_list = []
        if self.parent_name:
            final_list.append(self.parent_name)
        if self.inner_puzzle_hash:
            final_list.append(self.inner_puzzle_hash)
        if self.amount:
            final_list.append(self.amount)
        return Program.to(final_list)

    def is_none(self) -> bool:
        return not (self.parent_name or self.inner_puzzle_hash or self.amount)

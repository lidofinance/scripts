# copied from lido-oracle
import json
from abc import abstractmethod, ABC
from dataclasses import dataclass
from functools import reduce
from typing import Collection, Generic, Iterable, Sequence, TypedDict, TypeVar, TypeAlias

from hexbytes import HexBytes
from eth_abi.abi import encode
from eth_hash.auto import keccak
from eth_typing import TypeStr

Shares: TypeAlias = int
NodeOperatorId: TypeAlias = int
Pubkey: TypeAlias = bytes
Strikes: TypeAlias = list[int]
RewardTreeLeaf: TypeAlias = tuple[NodeOperatorId, Shares]
StrikesTreeLeaf: TypeAlias = tuple[NodeOperatorId, Pubkey, Strikes]
ICSTreeLeaf: TypeAlias = str


class TreeJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return f"0x{o.hex()}"
        return super().default(o)

class MerkleTree(ABC):
    """Merkle Tree interface"""

    @property
    @abstractmethod
    def root(self) -> bytes: ...

    @abstractmethod
    def find(self, leaf: bytes) -> int: ...

    @abstractmethod
    def get_proof(self, index: int) -> Iterable[bytes]: ...

    @abstractmethod
    def get_multi_proof(self, indices: Collection[int]) -> tuple[Iterable[bytes], Iterable[bool]]: ...

    @classmethod
    @abstractmethod
    def verify(cls, root: bytes, leaf: bytes, proof: Iterable[bytes]) -> bool: ...

    @classmethod
    @abstractmethod
    def __hash_leaf__(cls, leaf: bytes) -> bytes: ...

    @classmethod
    @abstractmethod
    def __hash_node__(cls, lhs: bytes, rhs: bytes) -> bytes: ...


class CompleteBinaryMerkleTree(MerkleTree):
    """The tree shaped as a [complete binary tree](https://xlinux.nist.gov/dads/HTML/completeBinaryTree.html)."""

    tree: tuple[bytes, ...]

    def __init__(self, leaves: Collection[bytes]):
        if not leaves:
            raise ValueError("Attempt to create an empty tree")

        tree = [b""] * (2 * len(leaves) - 1)

        for i, leaf in enumerate(leaves):
            tree[len(tree) - 1 - i] = leaf

        for i in range(len(tree) - 1 - len(leaves), -1, -1):
            tree[i] = self.__hash_node__(tree[2 * i + 1], tree[2 * i + 2])

        self.tree = tuple(tree)

    @property
    def root(self) -> bytes:
        return self.tree[0]

    def find(self, leaf: bytes) -> int:
        try:
            return self.tree.index(leaf)
        except ValueError as e:
            raise ValueError("Node not found") from e

    def get_proof(self, index: int) -> Iterable[bytes]:
        i = index
        while i > 0:
            yield self.tree[i - (-1) ** (i % 2)]
            i = (i - 1) // 2

    def get_multi_proof(self, indices: Collection[int]) -> tuple[Iterable[bytes], Iterable[bool]]:
        if not indices:
            return [], []

        indices = sorted(set(indices))
        n = len(self.tree)
        leaves_count = (n + 1) // 2

        proof = []
        flags = []

        def collect_proof_and_flags(idx: int) -> bool:
            if idx >= n:
                return False
            if idx >= n - leaves_count:
                return idx in indices

            left = 2 * idx + 1
            right = 2 * idx + 2
            left_needed = collect_proof_and_flags(left) if left < n else False
            right_needed = collect_proof_and_flags(right) if right < n else False

            if left_needed and right_needed:
                flags.append(True)
                return True
            elif left_needed:
                if right < n:
                    proof.append(self.tree[right])
                flags.append(False)
                return True
            elif right_needed:
                if left < n:
                    proof.append(self.tree[left])
                flags.append(False)
                return True

            return False

        collect_proof_and_flags(0)
        return proof, flags

    @classmethod
    def verify(cls, root: bytes, leaf: bytes, proof: Iterable[bytes]) -> bool:
        return reduce(lambda a, b: cls.__hash_node__(a, b), proof, leaf) == root

    @classmethod
    def verify_multi_proof(cls, root: bytes, leaves: list[bytes], proof: list[bytes], flags: list[bool]) -> bool:
        if not leaves:
            return True

        if len(leaves) + len(proof) - 1 != len(flags):
            return False

        queue = list(leaves)
        proof_idx = 0

        for flag in flags:
            if flag:
                if len(queue) < 2:
                    return False
                a = queue.pop(0)
                b = queue.pop(0)
            else:
                if len(queue) < 1 or proof_idx >= len(proof):
                    return False
                a = queue.pop(0)
                b = proof[proof_idx]
                proof_idx += 1

            queue.append(cls.__hash_node__(a, b))

        if proof_idx != len(proof):
            return False

        return len(queue) == 1 and queue[0] == root


T = TypeVar("T", bound=Iterable)


class Value(TypedDict):
    value: T
    treeIndex: int


class Dump(TypedDict):
    format: str
    leafEncoding: Iterable[TypeStr]
    tree: Collection[bytes]
    values: Sequence[Value[T]]


class StandardMerkleTree(Generic[T], CompleteBinaryMerkleTree):
    """
    OpenZeppelin Standard Merkle Tree

    - The tree is shaped as a complete binary tree.
    - The leaves are sorted.
    - The leaves are the result of ABI encoding a series of values.
    - The hash used is Keccak256.
    - The leaves are double-hashed to prevent second preimage attacks.
    """

    encoding: Iterable[TypeStr]
    values: Sequence[Value[T]]

    FORMAT = "standard-v1"

    def __init__(self, values: Sequence[T], encoding: Iterable[TypeStr]):
        self.encoding = encoding

        leaves = tuple(sorted(self.leaf(v) for v in values))
        super().__init__(leaves)

        self.values = tuple({"value": v, "treeIndex": self.find(self.leaf(v))} for v in values)

    def leaf(self, value: T) -> bytes:
        return self.__hash_leaf__(encode(self.encoding, value))

    def dump(self) -> Dump[T]:
        return {
            "format": self.FORMAT,
            "leafEncoding": self.encoding,
            "tree": self.tree,
            "values": self.values,
        }

    @classmethod
    def load(cls, data: Dump[T]):
        if "format" not in data or data["format"] != cls.FORMAT:
            raise ValueError("Unexpected dump format value")
        if "leafEncoding" not in data:
            raise ValueError("No leaf encoding provided")
        if "values" not in data:
            raise ValueError("No values provided")
        return cls([e["value"] for e in data["values"]], data["leafEncoding"])

    @classmethod
    def __hash_leaf__(cls, leaf: bytes) -> bytes:
        return keccak(keccak(leaf))

    @classmethod
    def __hash_node__(cls, lhs: bytes, rhs: bytes) -> bytes:
        if lhs > rhs:
            lhs, rhs = rhs, lhs
        return keccak(lhs + rhs)


@dataclass
class RewardsTree:
    """A wrapper around StandardMerkleTree to cover use cases of the CSM oracle"""

    tree: StandardMerkleTree[RewardTreeLeaf]

    @property
    def root(self) -> HexBytes:
        return HexBytes(self.tree.root)

    @classmethod
    def decode(cls, content: bytes):
        """Restore a tree from a supported binary representation"""

        try:
            return cls(StandardMerkleTree.load(json.loads(content)))
        except json.JSONDecodeError as e:
            raise ValueError("Unsupported tree format") from e

    def encode(self) -> bytes:
        """Convert the underlying StandardMerkleTree to a binary representation"""

        return (
            TreeJSONEncoder(
                indent=None,
                separators=(',', ':'),
                sort_keys=True,
            )
            .encode(self.dump())
            .encode()
        )

    def dump(self) -> Dump[RewardTreeLeaf]:
        return self.tree.dump()

    @classmethod
    def new(cls, values: Sequence[RewardTreeLeaf]):
        """Create new instance around the wrapped tree out of the given values"""
        return cls(StandardMerkleTree(values, ("uint256", "uint256")))


@dataclass
class StrikesTree:
    """A wrapper around StandardMerkleTree to cover use cases of the CSM oracle"""

    tree: StandardMerkleTree[StrikesTreeLeaf]

    @property
    def root(self) -> HexBytes:
        return HexBytes(self.tree.root)

    @classmethod
    def decode(cls, content: bytes):
        """Restore a tree from a supported binary representation"""

        try:
            return cls(StandardMerkleTree.load(json.loads(content)))
        except json.JSONDecodeError as e:
            raise ValueError("Unsupported tree format") from e

    def encode(self) -> bytes:
        """Convert the underlying StandardMerkleTree to a binary representation"""

        return (
            TreeJSONEncoder(
                indent=None,
                separators=(',', ':'),
                sort_keys=True,
            )
            .encode(self.dump())
            .encode()
        )

    def dump(self) -> Dump[StrikesTreeLeaf]:
        return self.tree.dump()

    @classmethod
    def new(cls, values: Sequence[StrikesTreeLeaf]):
        """Create new instance around the wrapped tree out of the given values"""
        return cls(StandardMerkleTree(values, ("uint256", "bytes", "uint256[]")))


@dataclass
class ICSTree:
    """A wrapper around StandardMerkleTree to cover use cases of the CSM ICS Vetted Gate"""

    tree: StandardMerkleTree[ICSTreeLeaf]

    @property
    def root(self) -> HexBytes:
        return HexBytes(self.tree.root)

    @classmethod
    def decode(cls, content: bytes):
        """Restore a tree from a supported binary representation"""

        try:
            return cls(StandardMerkleTree.load(json.loads(content)))
        except json.JSONDecodeError as e:
            raise ValueError("Unsupported tree format") from e

    def encode(self) -> bytes:
        """Convert the underlying StandardMerkleTree to a binary representation"""

        return (
            TreeJSONEncoder(
                indent=None,
                separators=(',', ':'),
                sort_keys=True,
            )
            .encode(self.dump())
            .encode()
        )

    def dump(self) -> Dump[ICSTreeLeaf]:
        return self.tree.dump()

    @classmethod
    def new(cls, values: Sequence[ICSTreeLeaf]):
        """Create new instance around the wrapped tree out of the given values"""
        values = [[value] for value in values]
        return cls(StandardMerkleTree(values, ("address",)))

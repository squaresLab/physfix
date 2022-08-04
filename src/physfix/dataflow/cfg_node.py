"""Data classes for CFG nodes"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Set, List

import attr
from physfix.parse.cpp_parser import Token
from physfix.parse.cpp_utils import token_to_stmt_str
from physfix.parse.dump_to_ast import FunctionDeclaration


class CFGNode(ABC):
    """Abstract class for CFGNode"""
    next: Set[CFGNode]
    previous: Set[CFGNode]

    @abstractmethod
    def get_type(self):
        """Returns type of CFGNode"""
        raise NotImplementedError

    def to_dict(self) -> Dict:
        """Serializes CFGNode to dictionary"""
        raise NotImplementedError


class EntryBlock(CFGNode):
    """Entry block for a function"""
    def __init__(self, function_declaration: FunctionDeclaration):
        self.next = set()
        self.previous = set()
        self.function_declaration = function_declaration
        self.function_arguments = list(function_declaration.function.argument.values())

    def get_type(self):
        return "entry"

    def __repr__(self):
        return f"EntryBlock(function_name={self.function_declaration.name})"

    def to_dict(self) -> Dict:
        entry_dict = {
            self.get_type(): {
                "name": self.function_declaration.name,
                "arguments": [v.nameToken.str for v in self.function_arguments],
            }
        }

        return entry_dict


@attr.s(eq=False, repr=False)
class ExitBlock(CFGNode):
    """Exit block for a function"""
    function_declaration: FunctionDeclaration = attr.ib()
    next: Set[CFGNode] = attr.ib(factory=set)
    previous: Set[CFGNode] = attr.ib(factory=set)

    def get_type(self):
        return "exit"

    def __repr__(self):
        return f"ExitBlock(function_name={self.function_declaration.name})"

    def to_dict(self) -> Dict:
        exit_block_dict = {
            self.get_type(): {
                "name": self.function_declaration.name
            }
        }

        return exit_block_dict


@attr.s(eq=False, repr=False)
class BasicBlock(CFGNode):
    """Node for a basic block"""
    token: Token = attr.ib()
    next: Set[CFGNode] = attr.ib(factory=set)
    previous: Set[CFGNode] = attr.ib(factory=set)

    def get_type(self):
        return "basic"

    def __repr__(self):
        return f"BasicBlock(token='{' '.join(token_to_stmt_str(self.token))}')"

    def to_dict(self) -> Dict:
        basic_block_dict = {
            self.get_type(): {
                "token": repr(self.token)
            }
        }

        return basic_block_dict


@attr.s(eq=False, repr=False)
class ConditionalBlock(CFGNode):
    """Node for condition block"""
    condition: Token = attr.ib()
    condition_true: CFGNode = attr.ib()
    condition_false: CFGNode = attr.ib()
    next: Set[CFGNode] = attr.ib(factory=set)
    previous: Set[CFGNode] = attr.ib(factory=set)

    def get_type(self):
        return "conditional"

    def __repr__(self):
        return f"ConditionalBlock(condition={token_to_stmt_str(self.condition)}"

    def to_dict(self) -> Dict:
        condition_block_dict = {
            self.get_type(): {
                "condition": repr(self.condition),
                "condition_true": self.condition_true.to_dict(),
                "condition_false": self.condition_false.to_dict()
            }
        }

        return condition_block_dict


@attr.s(eq=False, repr=False)
class JoinBlock(CFGNode):
    """Node for join block"""
    next: Set[CFGNode] = attr.ib()
    previous: Set[CFGNode] = attr.ib(factory=set)

    def get_type(self):
        return "join"

    def __repr__(self):
        repr_str = "JoinBlock("

        prev_repr_str = []
        for p in self.previous:
            prev_repr_str.append(repr(p))

        repr_str = repr_str + ", ".join(prev_repr_str) + ")"

        return repr_str

    def to_dict(self) -> Dict:
        join_block_dict = {
            self.get_type(): {}
        }

        return join_block_dict


@attr.s(eq=False, repr=False)
class EmptyBlock(CFGNode):
    """Node for empty block"""
    next: Set[CFGNode] = attr.ib(factory=set)
    previous: Set[CFGNode] = attr.ib(factory=set)

    def get_type(self):
        return "empty"

    def __repr__(self):
        return "EmptyBlock()"

    def to_dict(self) -> Dict:
        empty_block_dict = {
            self.get_type(): {}
        }

        return empty_block_dict


class FunctionCFG:
    """CFGNode for Function"""
    def __init__(self, function_declaration: FunctionDeclaration, entry_block: EntryBlock):
        self.function_declaration = function_declaration
        self.entry_block = entry_block
        self.nodes = []

    def create_node_mapping(self) -> Dict[CFGNode, int]:
        """Creates a mapping from a CFGNode to a unique int.
        IDs are the index of the CFGNode in self.nodes
        """
        node_mapping = {}
        for idx, n in enumerate(self.nodes):
            node_mapping[n] = idx

        return node_mapping

    def create_adjacency_list(self) -> Dict[int]:
        """Creates adjacency list for nodes using mapping generated by 
        create_node_mapping
        """
        node_mapping = self.create_node_mapping()

        adjacency_list = {}
        for n in self.nodes:
            next_ids = []
            for next_n in n.next:
                next_ids.append(node_mapping[next_n])

            previous_ids = []
            for prev_n in n.previous:
                previous_ids.append(node_mapping[prev_n])

            adjacency_list[node_mapping[n]] = {
                "next": sorted(next_ids),
                "previous": sorted(previous_ids)
            }

        return adjacency_list

    def to_dict(self) -> List[Dict]:
        """Serializes nodes of CFG into maping of node IDs to CFGNodes"""
        serialized_nodes_dict: Dict[int, Dict] = {}
        node_mapping = self.create_node_mapping()
        adjacency_list = self.create_adjacency_list()

        for n, id in node_mapping.items():
            serialized_n = n.to_dict()
            next_ids = adjacency_list[id]["next"]
            previous_ids = adjacency_list[id]["previous"]

            serialized_n["next"] = next_ids
            serialized_n["previous"] = previous_ids

            serialized_nodes_dict[id] = serialized_n

        return serialized_nodes_dict

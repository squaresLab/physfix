"""Dataclasses for AST parsing"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import uuid

import attr

from .cpp_parser import Scope, Token
from .scope_node import ScopeNode


class Statement(ABC):
    """Abstract base class for AST statements"""

    @abstractmethod
    def get_type(self) -> str:
        """Returns statement type"""
        raise NotImplementedError

    def to_dict(self) -> Dict:
        """Serializes statement to dictionary"""
        raise NotImplementedError

@attr.s(repr=False)
class BlockStatement(Statement):
    """Single block statement"""
    root_token: Token = attr.ib()

    def get_type(self) -> str:
        return "block"

    def to_dict(self) -> Dict:
        return {self.get_type(): repr(self.root_token)}

    def __repr__(self):
        return f"BasicStatement(root_token='{repr(self.root_token)}')"

@attr.s(repr=False)
class IfStatement(Statement):
    """If statement"""
    condition: Token = attr.ib()
    condition_true: List[Statement] = attr.ib()
    condition_false: List[Statement] = attr.ib()

    def get_type(self) -> str:
        return "if"

    def to_dict(self) -> Dict:
        if_dict = {
            self.get_type(): {
                "condition": repr(self.condition),
                "condition_true": [s.to_dict() for s in self.condition_true],
                "condition_false": [s.to_dict() for s in self.condition_false]
            }
        }

        return if_dict

    def __repr__(self):
        return f"IfStatement(condition='{repr(self.condition)}'"

@attr.s(repr=False)
class WhileStatement(Statement):
    """While statement"""
    condition: Token = attr.ib()  # Conditional
    condition_true: List[Statement] = attr.ib()  # While block

    def get_type(self) -> str:
        return "while"

    def to_dict(self) -> Dict:
        while_dict = {
            self.get_type(): {
                "condition": repr(self.condition),
                "condition_true": [s.to_dict() for s in self.condition_true]
            }
        }

        return while_dict

@attr.s()
class ForStatement(Statement):
    """For loop (all for loops should be desugared to while using .desugar)"""
    condition: Token = attr.ib()  # Conditional
    condition_true: List[Statement] = attr.ib()  # For block

    def get_type(self):
        return "for"

    def desugar(self) -> List[Union[BlockStatement, WhileStatement]]:
        """Desugars for loop into a while loop"""

        # E.g. int i = 0
        initialize_expr: Token = self.condition.astOperand1
        # E.g. i < 10
        condition_expr: Token = self.condition.astOperand2.astOperand1
        # E.g. i++
        update_expr: Token = self.condition.astOperand2.astOperand2

        blocks = []
        blocks.append(BlockStatement(initialize_expr))
        blocks.append(WhileStatement(condition_expr, self.condition_true + [BlockStatement(update_expr)]))

        return blocks

    def to_dict(self) -> Dict:
        raise ValueError("Desugar for into while")


@attr.s()
class SwitchStatment(Statement):
    """Switch statements represented as linked list (should be desugared into if statements)"""
    switch_expr: Token = attr.ib()
    match_expr: Token = attr.ib()  # Case for single switch expression
    match_true: List[Statement] = attr.ib()  # Code executed if switch case matches
    has_break: bool = attr.ib(init=False, default=False)  # Whether case terminates with break
    is_default: bool = attr.ib(init=False, default=False)  # Whether this is a default case
    previous: Optional[SwitchStatment] = attr.ib(init=False, default=None)  # Previous node in LL
    next: Optional[SwitchStatment] = attr.ib(init=False, default=None)  # Next node in LL

    def _add_breaks(self):
        """Converts self into switch statements where every node has a break"""
        # Convert switch statements so every switch has a break
        cur_switch: SwitchStatment = self  # Last node in LL
        while cur_switch.next: 
            cur_switch = cur_switch.next

        cur_switch.has_break = True
        cur_switch = cur_switch.previous
        while cur_switch:
            if not cur_switch.has_break:
                cur_switch.match_true.extend(cur_switch.next.match_true)

            cur_switch = cur_switch.previous

    def _switch_to_if_else(self) -> IfStatement:
        """Converts a switch to an if/else. MUST run _add_breaks before"""
        equals_token: Token = Token(None)  # Hopefully this doesn't become a problem
        equals_token.Id = uuid.uuid4()
        equals_token.str = "=="
        equals_token.astOperand1 = self.switch_expr
        equals_token.astOperand2 = self.match_expr
        condition_true: List[Statement] = self.match_true[:-1]  # Last token is break/continue/pass which should be excluded
        condition_false = []

        if self.next:
            if self.next.is_default:
                condition_false = self.next.match_true
            else:
                condition_false = [self.next._switch_to_if_else()]

        if_statement = IfStatement(equals_token, condition_true, condition_false)

        return if_statement

    def desugar(self) -> IfStatement:
        """Desugars switch into if/else statements"""
        self._add_breaks()
        return self._switch_to_if_else()

    def get_type(self) -> str:
        return "switch"

    def to_dict(self) -> Dict:
        raise ValueError("Desugar switch to if")


@attr.s()
class FunctionDeclaration(Statement):
    """Function declaration"""
    name: str = attr.ib()
    token_start: Token = attr.ib()
    token_end: Token = attr.ib()
    scope_obj: Scope = attr.ib()
    scope_tree: ScopeNode = attr.ib()
    function: str = attr.ib()
    body: List[Statement] = attr.ib(init=False, factory=list)

    def get_type(self):
        return "function"

    def to_dict(self) -> Dict:
        function_dict = {
            self.get_type(): {
                "name": self.name,
                "body": [s.to_dict() for s in self.body]
            }
        }

        return function_dict

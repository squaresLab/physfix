from __future__ import annotations

import json
import uuid
from collections import deque
from typing import Dict, List, Set, Tuple, Union

import attr
from physfix.parse.cpp_utils import get_root_token
from physfix.dataflow.ast_to_cfg import CFGNode
from physfix.dataflow.dependency_graph import DependencyGraph, DependencyNode
from physfix.parse.cpp_parser import Token, Variable
from physfix.parse.cpp_utils import get_statement_tokens


@attr.s(eq=False)
class Error:
    root_token_id: str = attr.ib()
    error_token_id: str = attr.ib()
    error_type: str = attr.ib()
    dependency_node: DependencyNode = attr.ib(default=None)
    dependency_graph: DependencyGraph = attr.ib(default=None)
    cfgnode: CFGNode = attr.ib(default=None)
    root_token = attr.ib(default=None)
    error_token = attr.ib(default=None)

    @staticmethod
    def from_dict(phys_output_dict, dependency_graphs) -> List[Error]:
        # print(output_dict)
        error_dict = phys_output_dict["errors"]

        error_objs = []
        for e in error_dict:
            e_obj = Error(e["root_token_id"], e["token_id"], e["error_type"])

            for d in dependency_graphs:
                for n in d.nodes:
                    # TODO: Implies that addition/subtraction inconsistencies only happen in basic blocks, need to fix
                    if n.cfgnode.get_type() == "basic":
                        if n.cfgnode.token.Id == e_obj.root_token_id:
                            e_obj.root_token = n.cfgnode.token
                            e_obj.cfgnode = n.cfgnode
                            e_obj.dependency_node = n
                            e_obj.dependency_graph = d
                            for t in get_statement_tokens(e_obj.root_token):
                                if t.Id == e_obj.error_token_id:
                                    e_obj.error_token = t
                                    break
                    elif n.cfgnode.get_type() == "conditional":
                        conditional_root = get_root_token(n.cfgnode.condition)
                        if conditional_root.Id == e_obj.root_token_id:
                            e_obj.root_token = conditional_root.astOperand2
                            e_obj.cfgnode = n.cfgnode
                            e_obj.dependency_node = n
                            e_obj.dependency_graph = d
                            e_obj.error_token = e_obj.root_token

            error_objs.append(e_obj)

        return error_objs

@attr.s()
class PhysVar:
    var_name: str = attr.ib()
    var_id: str = attr.ib()
    units: List[Dict] = attr.ib()  # Units sorted by likelihood by Phys

    @staticmethod
    def from_dict(phys_output_dict) -> List[PhysVar]:
        # print(output_dict)
        var_dict = phys_output_dict["variables"]

        phys_var_objs = []
        for v in var_dict:
            var_name = v["var_name"]
            var_id = v["var_id"]

            units = []
            for u in v["units"]:
                if isinstance(u, list):
                    units.append(u[0])
                elif isinstance(u, dict):
                    units.append(u)

            phys_var_objs.append(PhysVar(var_name, var_id, units))

        return phys_var_objs

    @staticmethod
    def create_unit_map(phys_vars: List[PhysVar]) -> Dict[str, PhysVar]:
        unit_map = {}
        for p in phys_vars:
            unit_map[p.var_id] = p
        
        return unit_map


@attr.s()
class Change:
    token_to_fix: Token = attr.ib()
    changes: List[Token] = attr.ib()


def get_token_unit_map(phys_output_dict):
    return phys_output_dict["token_units"] 


def dependency_node_to_error_map(errors) -> Dict[Tuple[DependencyGraph, DependencyNode], Set[Error]]:
    """Maps dependency graph/node tuple to set of errors at that node"""
    dependency_error_map = {}  # Maps dependency graph/node tuple to set of errors at that node

    for e in errors:
        d_graph, d_node = e.dependency_graph, e.dependency_node
        if (d_graph, d_node) in dependency_error_map:
            dependency_error_map[(d_graph, d_node)].add(e)
        else:
            dependency_error_map[(d_graph, d_node)] = {e}

    return dependency_error_map


def get_connected_errors(errors: List[Error]) -> List[Set[Error]]:
    """Returns list of sets of errors which are connected in the dependency graph"""
    dependency_error_map = dependency_node_to_error_map(errors)

    connected_errors: List[Set[Error]] = []
    seen = set()

    for e in errors:
        if (e.dependency_graph, e.dependency_node) in seen:
            continue

        q = deque()
        q.append((e.dependency_graph, e.dependency_node))
        connected = []
        while q:
            cur = q.pop()

            if cur in seen:
                continue

            if not (cur[0] and cur[1]):
                continue

            connected.extend(dependency_error_map[cur])
            seen.add(cur)

            for n in cur[1].next:
                if (cur[0], n) in dependency_error_map:
                    q.append(dependency_error_map[(cur[0], n)])
            for n in cur[1].previous:
                if (cur[0], n) in dependency_error_map:
                    q.append(dependency_error_map[(cur[0], n)])

        connected_errors.append(connected)

    return connected_errors

def get_root_errors(connected_errors: Set[Error]):
    dependency_error_map = dependency_node_to_error_map(list(connected_errors))
    root_error = None

    seen = set()
    q = deque()
    q.append(connected_errors[0].dependency_node)

    dependency_graph = connected_errors[0].dependency_graph  # All nodes should be a part of the same graph
    while q:
        cur = q.pop()

        if cur in seen:  # This means loop so we arbitrarily assign root error
            root_error = connected_errors[0]
            break

        if (dependency_graph, cur) in dependency_error_map:
            node_root_error = None

            for e in dependency_error_map[(dependency_graph, cur)]:
                if not node_root_error:
                    node_root_error = e
                else:
                    if e.error_type != "VARIABLE_MULTIPLE_UNITS":
                        node_root_error = e

            root_error = node_root_error
        
        seen.add(cur)

        if cur.previous:
            q.extend(cur.previous)
    
    return root_error


def multiply_units(u1: Dict[str, Union[int, float]], u2: Dict[str, Union[int, float]]):
    new_unit = u1.copy()

    for unit_name, unit_expt in u2.items():
        if unit_name in new_unit:
            new_unit[unit_name] += unit_expt
        else:
            new_unit[unit_name] = unit_expt

    return new_unit


def divide_units(u1: Dict[str, Union[int, float]], u2: Dict[str, Union[int, float]]):
    new_unit = u1.copy()

    for unit_name, unit_expt in u2.items():
        if unit_name in new_unit:
            new_unit[unit_name] -= unit_expt
        else:
            new_unit[unit_name] = -1 * unit_expt

    return new_unit


def expt_units(u1: Dict[str, Union[int, float]], power: Union[int, float]):
    new_unit = u1.copy()

    for unit_name in new_unit:
        new_unit[unit_name] *= power

    return new_unit


def unit_diff(u1: Dict[str, Union[int, float]], u2: Dict[str, Union[int, float]]):
    """Calculates the unit that u1 would have to be multiplied by to get u2"""
    diff = {}

    for unit_name, unit_expt in u2.items():
        if unit_name in u1:
            if unit_expt - u1[unit_name] != 0:
                diff[unit_name] = unit_expt - u1[unit_name]
        else:
            diff[unit_name] = unit_expt

    return diff


def inverse_unit(lhs_unit, token, phys_var_map: Dict[str, PhysVar], token_unit_map: Dict[str, Dict]):
    error_correct_unit = lhs_unit

    cur = token
    while cur.astParent:
        parent = cur.astParent
        if parent.str == "*":
            other_operand = parent.astOperand1 if parent.astOperand2 == cur else parent.astOperand1

            if other_operand.variable:
                error_correct_unit = multiply_units(error_correct_unit, phys_var_map[other_operand.Id].units)
            else:
                error_correct_unit = multiply_units(error_correct_unit, token_unit_map[other_operand.Id].units)
        elif parent.str == "/":
            other_operand = parent.astOperand1 if parent.astOperand2 == cur else parent.astOperand1

            if other_operand.variable:
                error_correct_unit = divide_units(error_correct_unit, phys_var_map[other_operand.Id].units)
            else:
                error_correct_unit = divide_units(error_correct_unit, token_unit_map[other_operand.Id].units)
        elif parent.str == "(":
            if parent.astOperand1.str == "sqrt":
                error_correct_unit = expt_units(error_correct_unit, 2)
            # Maybe consider pow function in the future?

        cur = parent
    
    return error_correct_unit


def make_arithmetic_token(arithmetic_op) -> Token:
    new_token = Token(None)
    new_token.str = arithmetic_op
    new_token.Id = str(uuid.uuid4())
    new_token.isArithmeticalOp = True
    new_token.isOp = True

    return new_token

def copy_variable_token(var: Variable) -> Token:
    new_token = Token(None)
    new_token.str = var.nameToken.str
    new_token.Id = str(uuid.uuid4())
    new_token.varId = var.Id
    new_token.variableId = var.Id
    new_token.variable = var

    return new_token


def apply_unit_multiplication(token: Token, cur_unit: Dict, target_unit: Dict, phys_var_map, dependency_node, dependency_graph,
                              depth=5):
    """Given a token (t) with a current unit, attempt to transform t to have the target unit by 
    applying the rules t -> t * x or t -> t / x, where x is a variable which reaches t
    """
    # token_unit_diff = unit_diff(target_unit, cur_unit)
    reach_defs = dependency_graph.reach_definition[dependency_node.cfgnode]
    candidate_change_tuples = []

    q = []
    q.append(([], [], cur_unit))  # Tuple of vars to multiply by, vars to divide by, and the current unit difference
    # print(cur_unit, target_unit)
    for _ in range(depth):
        new_q = []
        for mult_vars, div_vars, units in q:
            if units == target_unit:
                candidate_change_tuples.append((mult_vars, div_vars))

            for r in reach_defs:
                reach_var = r.variable

                if reach_var.Id not in phys_var_map:
                    continue
                
                reach_units = phys_var_map[reach_var.Id].units[0]

                if not reach_units:
                    continue
                
                if reach_var not in div_vars:
                    multiplication_units = multiply_units(units, reach_units)
                    new_q.append((mult_vars + [reach_var], div_vars, multiplication_units))

                if reach_var not in mult_vars:
                    division_units = divide_units(units, reach_units) 
                    new_q.append((mult_vars, div_vars + [reach_var], division_units))
        
        q = new_q

    # Change tuples into a list of tokens which can be made into a tree later
    change_trees = []

    # print(get_statement_tokens(token.copy()))
    # print([x.str for x in get_statement_tokens(token.copy())])
    for mult_vars, div_vars in candidate_change_tuples:
        head = Token(None)
        cur = head
        for var in mult_vars:
            mult_token = make_arithmetic_token("*")
            mult_token.astParent = cur
            mult_token.astParentId = cur.Id

            var_token = copy_variable_token(var)
            var_token.astParent = mult_token
            var_token.astParentId = mult_token.Id

            mult_token.astOperand1 = var_token
            mult_token.astOperand1Id = var_token.Id

            cur.astOperand2 = mult_token
            cur.astOperand2Id = mult_token.Id
            cur = cur.astOperand2

        if not div_vars:
            var_token = token.copy()
            var_token.astParent = cur
            var_token.astParentId = cur.Id

            cur.astOperand2 = var_token
            cur.astOperand2Id = var_token.Id

            change_trees.append(head.astOperand2)
            continue

        new_div_vars = [token] + div_vars
        for idx, var in enumerate(new_div_vars):
            var_token = None
            if idx == len(new_div_vars) - 2:
                div_token = make_arithmetic_token("/")
                div_token.astParent = cur
                div_token.astParentId = cur.Id

                var_token_1 = None
                if isinstance(var, Variable):
                    var_token_1 = copy_variable_token(var)
                else:
                    var_token_1 = var.copy()

                var_token_1.astParent = div_token
                var_token_1.astParentId = div_token.Id

                var_token_2 = copy_variable_token(new_div_vars[idx + 1])

                var_token_2.astParent = div_token
                var_token_2.astParentId = div_token.Id

                div_token.astOperand1 = var_token_1
                div_token.astOperand1Id = var_token_1.Id

                div_token.astOperand2 = var_token_2
                div_token.astOperand2d = var_token_2.Id

                cur.astOperand2 = div_token
                cur.astOperand2Id = div_token.Id
                break

            div_token = make_arithmetic_token("/")
            div_token.astParent = cur
            div_token.astParentId = cur.Id

            if isinstance(var, Variable):
                var_token = copy_variable_token(var)
            else:
                var_token = var.copy()

            var_token.astParent = div_token
            var_token.astParentId = div_token.Id

            div_token.astOperand1 = var_token
            div_token.astOperand1Id = var_token.Id

            cur.astOperand2 = div_token
            cur.astOperand2Id = div_token.Id
            cur = cur.astOperand2
        
        change_trees.append(head.astOperand2)

    return change_trees

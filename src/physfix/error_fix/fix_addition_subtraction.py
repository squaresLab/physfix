from __future__ import annotations

import uuid
from typing import Dict, Union

from physfix.dataflow.ast_to_cfg import ASTToCFG
from physfix.dataflow.dependency_graph import (CFGToDependencyGraph)
from physfix.error_fix.phys_fix_utils import (Change, Error, PhysVar,
                                              get_error_dependency_node,
                                              get_token_unit_map)
from physfix.parse.cpp_parser import Token, Variable
from physfix.parse.cpp_utils import (get_statement_tokens,
                                     get_vars_from_statement, get_lhs_from_statement,
                                     get_rhs_from_statement)


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


def fix_addition_subtraction(error: Error, phys_var_map: Dict[str, PhysVar], token_unit_map: Dict[str, Dict],
                             max_fixes=5):
    """Make sure to run get_error_dependency_node on error before this"""
    error_tokens = get_statement_tokens(error.root_token)
    lhs_tokens = get_lhs_from_statement(error_tokens)
    rhs_tokens = get_rhs_from_statement(error_tokens)
    
    # Assume LHS only has one variable
    lhs_var = get_vars_from_statement(lhs_tokens)[0]
    lhs_unit = phys_var_map[lhs_var.Id].units[0]

    # Walk from error token to root token and do inverse operations to find what unit the error var should have
    error_token = error.error_token
    error_correct_unit = inverse_unit(lhs_unit, error_token, phys_var_map, token_unit_map)
    
    error_left_token = error_token.astOperand1
    error_right_token = error_token.astOperand2
    
    error_left_unit = None
    if error_left_token.variable:
        error_left_unit = phys_var_map[error_left_token.variable.Id].units[0]
    else:
        error_left_unit = token_unit_map[error_left_token.Id]

    error_right_unit = None
    if error_right_token.variable:
        error_right_unit = phys_var_map[error_right_token.variable.Id].units[0]
    else:
        error_right_unit = token_unit_map[error_right_token.Id]

    # Assumes that only one unit is incorrect
    token_to_fix = None
    token_to_fix_unit = None

    cur_token = None
    direction = None
    if error_right_unit != error_correct_unit:
        cur_token = error_right_token
        token_to_fix_unit = error_right_unit
        direction = "left"
    else:
        cur_token = error_left_token
        token_to_fix_unit = error_left_unit
        direction = "right"

    while True:
        if cur_token.varId:
            token_to_fix = cur_token
            break
        elif cur_token.str == "(":
            token_to_fix = cur_token
            break
        elif cur_token.str in ["*", "/"]:
            token_to_fix = cur_token
            break
        elif cur_token.str in ["+", "-"]:
            if direction == "left":
                cur_token = cur_token.astOperand1
            else:
                cur_token = cur_token.astOperand2

    candidate_changes = apply_unit_multiplication(token_to_fix, token_to_fix_unit, error_correct_unit, phys_var_map, 
                                                  error.dependency_node, error.dependency_graph)[:max_fixes]
    
    # Returns token to be replaced and all candidate replacements
    return Change(token_to_fix, candidate_changes)


if __name__ == "__main__":
    output = "/home/rewong/phys/src/test_19_output.json"
    dump = "/home/rewong/phys/ryan/control_flow/dump_to_ast_test/test_19.cpp.dump"

    cfgs = ASTToCFG().convert(dump)
    d_graphs = [CFGToDependencyGraph().create_dependency_graph(c) for c in cfgs]

    e = Error.from_dict(output)
    # print(e)
    e_dependency = get_error_dependency_node(e[0], d_graphs)
    phys_vars = PhysVar.from_dict(output)
    var_unit_map = PhysVar.create_unit_map(phys_vars)
    token_unit_map = get_token_unit_map(output)
    g = fix_addition_subtraction(e[0], var_unit_map, token_unit_map)
    # print(g)
    # print(var_unit_map)

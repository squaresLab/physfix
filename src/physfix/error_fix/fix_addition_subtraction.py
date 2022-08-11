from __future__ import annotations

from typing import Dict

from physfix.error_fix.error_fix_utils import (Change, Error, PhysVar, inverse_unit, apply_unit_multiplication)
from physfix.parse.cpp_utils import (get_statement_tokens,
                                     get_vars_from_statement, get_lhs_from_statement)


def fix_addition_subtraction(error: Error, phys_var_map: Dict[str, PhysVar], token_unit_map: Dict[str, Dict],
                             max_fixes=5):
    """Make sure to run get_error_dependency_node on error before this"""
    error_tokens = get_statement_tokens(error.root_token)
    lhs_tokens = get_lhs_from_statement(error_tokens)
    
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
    return [Change(token_to_fix, candidate_changes)]


if __name__ == "__main__":
    output = "/home/rewong/phys/src/test_19_output.json"
    # dump = "/home/rewong/phys/ryan/control_flow/dump_to_ast_test/test_19.cpp.dump"

    # cfgs = ASTToCFG().convert(dump)
    # d_graphs = [CFGToDependencyGraph().create_dependency_graph(c) for c in cfgs]

    # e = Error.from_dict(output)
    # # print(e)
    # e_dependency = get_error_dependency_node(e[0], d_graphs)
    # phys_vars = PhysVar.from_dict(output)
    # var_unit_map = PhysVar.create_unit_map(phys_vars)
    # token_unit_map = get_token_unit_map(output)
    # g = fix_addition_subtraction(e[0], var_unit_map, token_unit_map)
    # print(g)
    # print(var_unit_map)

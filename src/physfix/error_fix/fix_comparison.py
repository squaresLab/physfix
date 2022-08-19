from __future__ import annotations

from typing import Dict

from physfix.error_fix.error_fix_utils import (Change, Error, PhysVar, inverse_unit, apply_unit_multiplication)
from physfix.parse.cpp_utils import (get_statement_tokens,
                                     get_vars_from_statement, get_lhs_from_statement)

# TODO: I think there's something wrong in the process of creating these changes because some tokens are missing after applying the change to source code
def fix_comparison(error: Error, phys_var_map: Dict[str, PhysVar], token_unit_map: Dict[str, Dict],
                   max_fixes=5):
    """Make sure to run get_error_dependency_node on error before this"""
    error_tokens = get_statement_tokens(error.root_token)
    lhs_token_root = error.error_token.astOperand1
    rhs_token_root = error.error_token.astOperand2
    
    lhs_unit = None
    if lhs_token_root.variable:
        lhs_unit = phys_var_map[lhs_token_root.variable.Id].units[0]
    else:
        lhs_unit = token_unit_map[lhs_token_root.Id]

    rhs_unit = None
    if rhs_token_root.variable:
        rhs_unit = phys_var_map[rhs_token_root.variable.Id].units[0]
    else:
        rhs_unit = token_unit_map[rhs_token_root.Id]

    # Assumes that only one unit is incorrect
    changes = []
    changes.append(Change(lhs_token_root, 
                          apply_unit_multiplication(lhs_token_root, lhs_unit, rhs_unit, phys_var_map, 
                                                    error.dependency_node, error.dependency_graph)[:max_fixes]))
    changes.append(Change(rhs_token_root, 
                          apply_unit_multiplication(rhs_token_root, rhs_unit, lhs_unit, phys_var_map, 
                                                    error.dependency_node, error.dependency_graph)[:max_fixes]))

    # Returns token to be replaced and all candidate replacements
    return changes


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

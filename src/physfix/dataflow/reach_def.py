from __future__ import annotations

from collections import deque
from typing import Dict, Set, Tuple

import attr
from physfix.parse.cpp_parser import Variable
from physfix.parse.cpp_utils import (get_lhs_from_statement, get_rhs_from_statement,
                                     get_statement_tokens, get_vars_from_statement)
from physfix.dataflow.ast_to_cfg import CFGNode, FunctionCFG


@attr.s(eq=False)
class DefUsePair:
    """Variables defined/used in a cfg Node"""
    cfgnode: CFGNode = attr.ib()
    define: Set[Variable] = attr.ib(factory=set)
    use: Set[Variable] = attr.ib(factory=set)
    
    def to_dict(self) -> Dict:
        """Serializes DefUsePair to dictionary"""
        def_use_dict = {
            "node": self.cfgnode.to_dict(),
            "define": [v.nameToken.str for v in self.define],
            "use": [v.nameToken.str for v in self.use]
        }

        return def_use_dict

def create_def_use_pairs(cfg: FunctionCFG) -> Dict[CFGNode, DefUsePair]:
    """Maps every node in CFG to a dictionary containing a def, use pair"""
    def_use_pairs = {}
    queue = deque([cfg.entry_block])
    seen = set()

    while queue:
        cur = queue.popleft()

        if cur in seen:
            continue

        cur_type = cur.get_type()
        block_def_use = DefUsePair(cur)

        if cur_type == "entry":
            block_def_use.define.update(cur.function_arguments)
        elif cur_type == "basic":
            statement = get_statement_tokens(cur.token)
            lhs = get_lhs_from_statement(statement)
            rhs = get_rhs_from_statement(statement)

            if lhs:
                block_def_use.define.update(get_vars_from_statement(lhs))
            if rhs:
                block_def_use.use.update(get_vars_from_statement(rhs))
            else:
                block_def_use.use.update(get_vars_from_statement(statement))
        elif cur_type == "conditional":
            block_def_use.use.update(get_vars_from_statement(get_statement_tokens(cur.condition)))

        for next_node in cur.next:
            queue.append(next_node)

        seen.add(cur)
        def_use_pairs[cur] = block_def_use

    return def_use_pairs


@attr.s(eq=False)
class ReachDef:
    """Data class of a variable dn the CFGNode which defines it"""
    def_node: CFGNode = attr.ib()
    variable: Variable = attr.ib()

    def to_dict(self) -> Dict:
        """Serialized ReachDef to dict"""
        reach_def_dict = {
            "node": self.def_node.to_dict(),
            "variable": self.variable.nameToken.str
        }

        return reach_def_dict


def create_reach_definitions(cfg: FunctionCFG, 
                             def_use_pairs: Dict[CFGNode, DefUsePair]) -> Dict[CFGNode, Set[ReachDef]]:
    """Calculates variables that reach a node for all nodes in CFG. Returns a mapping 
    between CFGNodes and ReachNodes.
    """
    reach_def_map: Dict[Tuple(CFGNode, Variable), ReachDef] = {}
    reach_out: Dict[CFGNode, Set[ReachDef]] = {}
    reach: Dict[CFGNode, Set[ReachDef]] = {}
    for n in cfg.nodes:
        reach_out[n] = set()
        reach[n] = set()

    queue = deque(cfg.nodes)

    while queue:
        cur: CFGNode = queue.popleft()
        old_reach_out: Set[ReachDef] = reach_out[cur]

        reach_cur = set()
        for prev in cur.previous:
            reach_cur.update(reach_out[prev])
        reach[cur] = reach_cur

        gen: Set[ReachDef] = set()
        kill: Set[Variable] = set()
        new_reach_out: Dict[CFGNode, Set[ReachDef]] = set()
        if def_use_pairs[cur].define:
            for def_var in def_use_pairs[cur].define:
                if (cur, def_var) in reach_def_map:
                    gen.add(reach_def_map[(cur, def_var)])
                else:
                    new_reach_def = ReachDef(cur, def_var)
                    reach_def_map[(cur, def_var)] = new_reach_def
                    gen.add(new_reach_def)
                kill.add(def_var)

            new_reach_out.update(gen)
            for reach_def in reach[cur]:
                variable = reach_def.variable
                if variable not in kill:
                    new_reach_out.add(reach_def)
        else:  # If nothing is defined then then kill and gen are empty sets
            new_reach_out = reach[cur]

        reach_out[cur] = new_reach_out

        if new_reach_out != old_reach_out:
            queue.extend(cur.next)

    return reach
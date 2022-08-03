from __future__ import annotations

from collections import deque
from typing import Dict, List, Tuple, Set

import attr

from physfix.src.physfix.ast_to_cfg import ASTToCFG, CFGNode, FunctionCFG
from cpp_parser import Variable
from cpp_utils import (get_LHS_from_statement, get_RHS_from_statement,
                       get_statement_tokens, get_vars_from_statement)

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
            lhs = get_LHS_from_statement(statement)
            rhs = get_RHS_from_statement(statement)

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


@attr.s(eq=False, repr=False)
class DependencyNode:
    cfgnode: CFGNode = attr.ib()
    variable: Variable = attr.ib()
    next: Set[DependencyNode] = attr.ib(factory=set)
    previous: Set[DependencyNode] = attr.ib(factory=set)

    def to_dict(self) -> Dict:
        """Serializes DepenencyNode to dict"""
        dependency_node_dict = {
            "node": self.cfgnode.to_dict(),
            "variable": self.variable.nameToken.str,
        }

        return dependency_node_dict

    def __repr__(self):
        return str(self.to_dict())

@attr.s()
class DependencyGraph:
    cfg: FunctionCFG = attr.ib()
    nodes: List[DependencyNode] = attr.ib()
    reach_definition: Dict[CFGNode, Set[ReachDef]] = attr.ib()
    def_use_pairs: Dict[CFGNode, DefUsePair] = attr.ib()

    def create_node_mapping(self) -> Dict[CFGNode, int]:
        """Maps DependencyNode to a unique int. IDs are determined
        by ordering nodes based on CFGNode ID and then by alphabetical order
        of variable name.
        """
        cfg_node_mapping = self.cfg.create_node_mapping()
        node_groups = {}

        for i in range(len(cfg_node_mapping)):
            node_groups[i] = []

        for n in self.nodes:
            cfgnode = n.cfgnode
            node_groups[cfg_node_mapping[cfgnode]].append(n)

        for group in node_groups.values():
            group.sort(key=lambda x: x.variable.nameToken.str)

        ordered_nodes = []
        for group in node_groups.values():
            ordered_nodes.extend(group)

        node_mapping = {}
        for idx, n in enumerate(ordered_nodes):
            node_mapping[n] = idx

        return node_mapping

    def create_adjacency_list(self) -> Dict[int]:
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

    def get_connected_components(self) -> List[Set[DependencyNode]]:
        """Returns a list of sets containing connected components"""
        connected_components: List[Set[CFGNode]] = []
        all_nodes = deque(self.nodes)
        processed: Set[CFGNode] = set()

        while all_nodes:
            root = all_nodes.pop()
            if root in processed:
                continue

            q = deque([root])
            connected = set()
            while q:
                cur = q.pop()

                if cur in connected:
                    continue

                connected.add(cur)
                processed.add(cur)
                for n in cur.next:
                    q.append(n)
                for n in cur.previous:
                    q.append(n)

            connected_components.append(connected)

        return connected

    def get_node_connected_components(self, dependency_node) -> Set[DependencyNode]:
        connected = set()
        seen = set()
        q = deque()
        q.append(dependency_node)

        while q:
            cur = q.pop()
            if cur in seen:
                continue

            connected.add(cur)

            for n in cur.next:
                q.append(n)
            for n in cur.previous:
                q.append(n)

            seen.add(cur)

        return connected

    # def get_root_variables(self) -> List[DependencyNode]:
    #     """Returns all root nodes of graph"""
    #     connected_components = self.get_connected_components()
    #     root_variables = []

    #     for c in connected_components:
    #         for n in c:
    #             if not n.previous


class CFGToDependencyGraph:
    def __init__(self):
        pass

    @staticmethod
    def create_dependency_graph(cfg: FunctionCFG) -> List[DependencyNode]:
        # Maps CFGNode to set of ReachDef which represent variables which are used to define other variables
        # in CFGNode
        node_dependency_mapping: Dict[CFGNode, Set[ReachDef]] = {}
        def_use_pairs = create_def_use_pairs(cfg)
        reach_definitions = create_reach_definitions(cfg, def_use_pairs)

        # Get all variables which are used to define other variables in each node
        for cur_node, reach_def in reach_definitions.items():
            cur_def: Set[Variable] = def_use_pairs[cur_node].define
            cur_use: Set[Variable] = def_use_pairs[cur_node].use
            remove = set()

            if not cur_def:
                continue
            
            for r in reach_def:
                reach_var = r.variable
                # If the variable is killed by the statement or if variable isn't used in statement
                if reach_var in cur_def or reach_var not in cur_use:
                    remove.add(r)

            node_dependency_mapping[cur_node] = reach_definitions[cur_node].copy()
            node_dependency_mapping[cur_node] -= remove

        cfg_dependency_node_mapping = {}  # Maps CFGNode to set of DependencyNodes
        dependency_graph_nodes = []  # All DependencyNodes
        # Create all nodes of dependency graph for all variables in each node
        for cur_node in node_dependency_mapping:
            cfg_dependency_node_mapping[cur_node] = set()
            cur_def = def_use_pairs[cur_node].define

            for def_var in cur_def:
                cfg_dependency_node_mapping[(cur_node, def_var)] = set()
                d_node = DependencyNode(cur_node, def_var)
                dependency_graph_nodes.append(d_node)
                cfg_dependency_node_mapping[(cur_node, def_var)].add(d_node)

        # Set previous and next nodes for all dependency nodes
        for d in dependency_graph_nodes:
            reach_def = node_dependency_mapping[d.cfgnode]

            for r in reach_def:
                prev = cfg_dependency_node_mapping[(r.def_node, r.variable)]
                d.previous.update(prev)

                for p in prev:
                    p.next.add(d)

        dependency_graph = DependencyGraph(cfg, dependency_graph_nodes, reach_definitions,
                                           def_use_pairs)
        return dependency_graph


if __name__ == "__main__":
    cfg = ASTToCFG.convert("/home/rewong/phys/ryan/control_flow/data_dependency_test/test_2.cpp.dump")
    # p = create_def_use_pairs(cfg[0])
    # print(p)
    # print("____")
    # for k, v in p.items():
    #     if k.get_type() == "basic":
    #         print(token_to_stmt_str(k.token))
    #         print(f"def {[x.nameToken.str for x in v['def']]}")
    #         print(f"use {[x.nameToken.str for x in v['use']]}")

    # r = create_reach_definitions(cfg[0], p)
    # print(r)

    # for k, v in r.items():
    #     print("____")
    #     print(k)
    #     for x in v:
    #         print(x)
    # print(p)
    g = CFGToDependencyGraph().create_dependency_graph(cfg[0])
    print(g.to_dict())
    # print(r)
    # for k, v in r.items():
    #     print("___")
    #     print(f"{k}:")
    #     for (n, var) in v:
    #         print(n, var)
    # for k, v in r.items():
    #     if k.get_type() == "basic":
    #         print("____")
    #         print(token_to_stmt_str(k.token))
            
    #         for n, var in v:
    #             if n.get_type() == "basic":
    #                 print(f"{token_to_stmt_str(n.token)}: {var.nameToken.str}")
    #             elif n.get_type() == "entry":
    #                 print(f"Entry: {var.nameToken.str}")

        

"""Converting Statement objects into CFGs"""
from __future__ import annotations

import json
from typing import Dict, List, Tuple

import yaml
from physfix.dataflow.cfg_node import (BasicBlock, CFGNode, ConditionalBlock,
                                       EmptyBlock, EntryBlock, ExitBlock,
                                       FunctionCFG, JoinBlock)
from physfix.parse.cpp_utils import (get_statement_tokens, token_to_stmt_str,
                                     tokens_to_str)
from physfix.parse.dump_to_ast import DumpToAST, Statement


class ASTToCFG:
    """Class for converting AST to CFG"""
    def __init__(self, dump_to_ast: DumpToAST):
        self.dump_to_ast = dump_to_ast

        if not self.dump_to_ast.function_declaration_objs:
            self.dump_to_ast.convert()

        self.function_declaration_objs = self.dump_to_ast.function_declaration_objs
        self.function_cfgs = []

    def convert(self) -> List[FunctionCFG]:
        """Takes a dump file path and creates a CFG for each function"""
        for f in self.function_declaration_objs:
            entry_block = EntryBlock(f)
            exit_block = ExitBlock(f)
            f_cfg = FunctionCFG(f, entry_block)
            f_cfg.nodes.append(entry_block)

            body = self._convert_statements(f.body, [(f.get_type(), entry_block, exit_block)], f_cfg)
            entry_block.next.add(body)

            if body:
                body.previous.add(entry_block)

            f_cfg.nodes.append(exit_block)
            self.function_cfgs.append(f_cfg)

        return self.function_cfgs

    def _convert_statements(self, statements: List[Statement], call_tree: List[Tuple[str, Statement, Statement]],
                            function_cfg: FunctionCFG) -> EntryBlock:
        """call_tree is order of block calls and each item is tuple of the call + start block of call + the exit/join block of that call"""
        sentinel = EmptyBlock()  # Sentinel node
        cur = sentinel  # Cur node in graph

        for stmt in statements:
            if stmt.get_type() == "block":  # Block statement -> BasicBlock
                # Make basic block, connect to cur, advance cur
                basic_block = BasicBlock(stmt.root_token)
                function_cfg.nodes.append(basic_block)
                basic_block.previous.add(cur)
                cur.next.add(basic_block)
                cur = basic_block

                # Walk through AST to check for break/return/continue
                for t in get_statement_tokens(stmt.root_token):
                    if t.str == "break":
                        assert call_tree, "No call tree"

                        # Find where to break out of
                        last_while = None
                        for i in range(len(call_tree) - 1, -1, -1):
                            if call_tree[i][0] == "while":
                                last_while = call_tree[i]
                                break

                        assert last_while, "Attempted to break with no while"

                        cur.next.add(last_while[2])
                        last_while[2].previous.add(cur)

                        start = sentinel.next.pop()
                        start.previous.remove(sentinel)
                        return start
                    elif t.str == "return":
                        assert call_tree, "No call tree"
                        block_type, _, block_exit = call_tree[0]
                        assert block_type == "function", "Attempted to return outside a function"

                        # Connect return statement to function exit block
                        cur.next.add(block_exit)
                        block_exit.previous.add(cur)

                        start = sentinel.next.pop()
                        start.previous.remove(sentinel)
                        return start
                    elif t.str == "continue":
                        assert call_tree, "No call tree"

                        # Find where to continue to
                        last_while = None
                        for i in range(len(call_tree) - 1, -1, -1):
                            if call_tree[i][0] == "while":
                                last_while = call_tree[i]
                                break

                        assert last_while, "Attempted to continue with no while"

                        cur.next.add(last_while[1])
                        last_while[1].previous.add(cur)

                        start = sentinel.next.pop()
                        start.previous.remove(sentinel)
                        return start

            elif stmt.get_type() == "if":
                cond_block = ConditionalBlock(stmt.condition, None, None)
                function_cfg.nodes.append(cond_block)
                cur.next.add(cond_block)
                cond_block.previous.add(cur)
                join_block = JoinBlock(set())

                # Recursively get true/false nodes
                condition_true = self._convert_statements(stmt.condition_true, call_tree + [("if", cond_block, join_block)],
                                                          function_cfg)
                condition_false = self._convert_statements(stmt.condition_false, call_tree + [("if", cond_block, join_block)],
                                                           function_cfg)

                cond_block.condition_true = condition_true
                cond_block.next.add(condition_true)
                condition_true.previous.add(cond_block)

                condition_true_end = self._convert_traverse(condition_true)

                if condition_true_end is not None:
                    condition_true_end = condition_true_end[-1]
                    condition_true_end.next.add(join_block)
                    join_block.previous.add(condition_true_end)

                cond_block.condition_false = condition_false
                cond_block.next.add(condition_false)
                condition_false.previous.add(cond_block)

                condition_false_end = self._convert_traverse(condition_false)
                if condition_false_end is not None:            
                    condition_false_end = condition_false_end[-1]
                    condition_false_end.next.add(join_block)
                    join_block.previous.add(condition_false_end)

                if condition_false_end or condition_true_end:
                    function_cfg.nodes.append(join_block)

                cur = join_block
            elif stmt.get_type() == "while":
                cond_block = ConditionalBlock(stmt.condition, None, None)
                function_cfg.nodes.append(cond_block)
                cur.next.add(cond_block)
                cond_block.previous.add(cur)
                join_block = JoinBlock(set())

                # Recursively get true/false nodes
                condition_true = self._convert_statements(stmt.condition_true, call_tree + [("while", cond_block, join_block)],
                                                          function_cfg)
                condition_false = EmptyBlock()
                function_cfg.nodes.append(condition_false)

                # Connect true/false to conditional
                cond_block.condition_true = condition_true
                cond_block.next.add(condition_true)
                condition_true.previous.add(cond_block)
                cond_block.condition_false = condition_false
                cond_block.next.add(condition_false)
                condition_false.previous.add(cond_block)

                # Traverse to end of conditionals
                condition_true_end = self._convert_traverse(condition_true)
                if condition_true_end:
                    condition_true_end = condition_true_end[-1]

                    if condition_true_end.get_type() == "basic" and "break" not in token_to_stmt_str(condition_true_end.token):
                        condition_true_end.next.add(cond_block)
                        cond_block.previous.add(condition_true_end)
                    elif condition_true_end.get_type() != "basic":
                        condition_true_end.next.add(cond_block)
                        cond_block.previous.add(condition_true_end)

                condition_false_end = condition_false  # End of empty block is just the empty block

                # Connect false to join
                condition_false_end.next.add(join_block)
                join_block.previous.add(condition_false_end)

                if condition_true_end or condition_false_end:
                    function_cfg.nodes.append(join_block)

                cur = join_block
            else:
                raise ValueError(f"Unexpected statement: {stmt.get_type()}")

        if call_tree and len(call_tree) == 1 and call_tree[0][0] == "function":  # If we're in the top level function block
            function_exit_block = call_tree[0][2]

            if cur.previous:  # Check that cur isn't dangling
                cur.next.add(function_exit_block)
                function_exit_block.previous.add(cur)

        if sentinel.next:
            assert len(sentinel.next) == 1, "Too many nodes"

            start = sentinel.next.pop()
            start.previous.pop()
            return start

        empty_return = EmptyBlock()
        function_cfg.nodes.append(empty_return)
        return empty_return

    def _convert_traverse(self, node: CFGNode) -> List[CFGNode]:
        """Traverses nodes of a CFG"""

        def traverse(path):
            if not path[-1].next:
                return path

            cur_node = path[-1]
            if cur_node.get_type() == "basic":
                for t in tokens_to_str(get_statement_tokens(cur_node.token)):
                    if t in ["return", "break", "continue"]:
                        return None
            elif cur_node.get_type() == "exit":
                return None

            for next_node in path[-1].next:
                if next_node in path:
                    continue

                res = traverse(path + [next_node])
                if res:
                    return res

            return None

        return traverse([node])

    def write(self, file_name: str, serialize_format="yaml"):
        """Serializes FunctionDeclaration objects to yaml/json"""
        objs_dict: Dict = [c.to_dict() for c in self.function_cfgs]

        if serialize_format == "yaml":
            with open(file_name, "w", encoding="utf-8") as f:
                yaml.dump(objs_dict, f)
        elif serialize_format == "json":
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(objs_dict, f)
        else:
            raise ValueError("Format should be json or yaml")


def main():
    # e_count = 0
    test_path = f"/home/rewong/physfix/tests/ast_to_cfg_test/test_12.cpp.dump"
    parsed = ASTToCFG.convert(test_path)
    print(parsed[0].nodes)
    # print(parsed[0].to_dict())
    # ASTToCFG.write(parsed, "test_2.yaml")
    # e_count = 0
    # with open("dump_files.txt") as f:
    #     for idx, l in enumerate(f.readlines()):
    #         print(idx)
    #         try:
    #             test_path = f"/home/rewong/{l.rstrip()}"
    #             parsed = ASTToCFG.convert(test_path)
    #         except Exception as e:
    #             print(test_path)
    #             print(e)
    #             e_count += 1
    # print(e_count)
    
    # print(e_count)
    # x = parsed[0].next.pop().next.pop().condition_false.next.pop().previous
    # x = list(list(parsed[0].next)[0].next)[0].condition_true.condition_false.next.pop().next
    # y = list(list(list(parsed[0].next)[0].next)[0].condition_false.next)[0]
    # print(tokens_to_str(get_statement_tokens(x.condition)))
    # print(x)
    # for i in x:
    #     if i.get_type() == "conditional":
    #         for j in i.next:
    #             print(j.next.pop().next.pop().previous, j.get_type())
    # print(tokens_to_str(get_statement_tokens(parsed[0].next.pop().next.pop().next.pop().next.pop().next.pop().next)))

    # print([x.scope_obj.type for x in parsed[0].scope_tree.children])

    # cur = [parsed[0].scope_tree]
    # while cur:
    #     x = cur.pop(0)
    #     print(x.scope_id)
    #     print([z.scope_id for z in x.children])
    #     cur.extend(x.children)

    # print_AST(parsed[0].body)
    # print(parsed[0].body[-1].condition_true[2])
    # print_AST(parsed[0].body[-1].match_true[-1].match_true)
    # for b in parsed[0].body:
    #     print("_____")
    #     if b.type == "block":
    #         print(tokens_to_str(get_statement_tokens(b.root_token)))
    #     elif b.type == "if":
    #         print(tokens_to_str(get_statement_tokens(b.condition)))
    #         print(b.condition_true)
            # print(tokens_to_str(get_statement_tokens(b.condition_true)))
            # print(tokens_to_str(get_statement_tokens(b.condition_false)))

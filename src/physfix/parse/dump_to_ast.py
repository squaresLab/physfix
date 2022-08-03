"""Converting cppcheck dump files into AST Statements objects"""
from __future__ import annotations

import json
from typing import Dict, List

import yaml

from .cpp_parser import CppcheckData, Token
from .cpp_utils import (get_functions, get_root_tokens, get_statement_tokens,
                        tokens_to_str)
from .scope_node import ScopeNode
from .statement import (BlockStatement, ForStatement, FunctionDeclaration,
                        IfStatement, Statement, SwitchStatment, WhileStatement)


class DumpToAST:
    """Class for parsing an Cppcheck XML dump into an AST tree"""
    def __init__(self, dump_file_path: str):
        self.dump_file_path = dump_file_path
        self.cpp_check_data = CppcheckData(dump_file_path)
        self.cpp_check_config = self.cpp_check_data.configurations[0]

        self.function_declaration_objs: List[FunctionDeclaration] = []

    def convert(self) -> List[FunctionDeclaration]:
        """Converts self.cpp_check_config into an AST for each function"""

        # Loop through all functions in file
        for f in get_functions(self.cpp_check_config).values():
            func_obj = FunctionDeclaration(f["name"], f["token_start"], f["token_end"], 
                                           f["scopeObject"], 
                                           ScopeNode.make_scope_tree(self.cpp_check_config, f["scopeObject"]),
                                           f["function"])
            # print(f["name"])
            # Get root tokens for all statements inside of function
            root_tokens = get_root_tokens(func_obj.token_start, func_obj.token_end)
            # Parse into AST
            func_obj.body = parse(root_tokens, func_obj.scope_tree.copy())
            self.function_declaration_objs.append(func_obj)

        return self.function_declaration_objs

    def _parse(self, root_tokens: List[Token], scope_tree: ScopeNode) -> List[Statement]:
        """Parses root tokens into AST Statement objects"""
        blocks: List[Statement] = []

        while root_tokens:
            t: Token = root_tokens.pop(0)

            # If block
            if t.astOperand1 and t.astOperand1.str == "if":
                # # print(f"Inside scope tree {scope_tree}")
                # # Grab the scope from scope tree
                # if_scope: ScopeNode = scope_tree.children[0]
                # assert if_scope.scope_obj.type == "If", f"Expected if scope, got {if_scope.scope_obj.type}"
                # # Remove scope from tree so it isn't reused
                # scope_tree.remove_by_id(if_scope.scope_id)
                # # Find end of scope (denoted by '}')
                # if_scope_end: Token = if_scope.scope_obj.classEnd
                # # Grab if statement conditional
                # conditional_root_token = t.astOperand2

                # # Get tokens for true case
                # condition_true_root_tokens: List[Token] = []

                # # Get tokens that are before the scope end
                # cur_token: Token = if_scope.scope_obj.classStart
                # while root_tokens and cur_token.Id != if_scope_end.Id:
                #     if cur_token.Id == root_tokens[0].Id:
                #         condition_true_root_tokens.append(root_tokens.pop(0))

                #     cur_token = cur_token.next

                # # Recursively parse tokens
                # condition_true: List[Statement] = parse(condition_true_root_tokens, if_scope)

                # # Check backwards in scope for break/continue
                # break_continue_token = None
                # cur_token: Token = if_scope_end
                # while cur_token and cur_token.scopeId == if_scope_end.scopeId:
                #     if cur_token.str in ["break", "continue"]:
                #         break_continue_token = cur_token
                #         break  # Haha get it?

                #     cur_token = cur_token.previous

                # if break_continue_token:
                #     # Assumed that break/continue is always at the end of a statement
                #     condition_true.append(BlockStatement(break_continue_token))

                # # Get tokens for false/else case
                # condition_false_root_tokens: List[Token] = []
                # condition_false: List[Statement] = []
                # # Check if Else scope exists and directly follows If scope
                # if scope_tree.children and scope_tree.children[0].scope_obj.type == "Else":
                #     else_scope: ScopeNode = scope_tree.children[0]
                #     else_scope_end: Token = else_scope.scope_obj.classEnd
                #     scope_tree.remove_by_id(if_scope.scope_id)

                #     condition_false_root_tokens: List[Token] = []

                #     cur_token: Token = else_scope.scope_obj.classStart
                #     while root_tokens and cur_token.Id != else_scope_end.Id:
                #         if cur_token.Id == root_tokens[0].Id:
                #             condition_false_root_tokens.append(root_tokens.pop(0))

                #         cur_token = cur_token.next

                #     if condition_false_root_tokens:
                #         condition_false = parse(condition_false_root_tokens, else_scope)

                #     break_continue_token = None
                #     cur_token: Token = else_scope_end

                #     # Check backwards in scope for break/continue
                #     while cur_token and cur_token.scopeId == else_scope_end.scopeId:
                #         if cur_token.str in ["break", "continue"]:
                #             break_continue_token = cur_token
                #             break  # Haha get it?

                #         cur_token = cur_token.previous

                #     if break_continue_token:
                #         # Assumed that break/continue is always at the end of a statement
                #         condition_false.append(BlockStatement(break_continue_token))

                # blocks.append(IfStatement(conditional_root_token, condition_true, condition_false))
                if_statement = self._parse_if(t, root_tokens, scope_tree)
                blocks.append(if_statement)
            # While statement
            elif t.astOperand1 and t.astOperand1.str == "while":
                # # Grab while scope from tree
                # while_scope: ScopeNode = scope_tree.children[0]
                # assert while_scope.scope_obj.type == "While", f"Expected while scope, got {while_scope.scope_obj.type}"
                # # Remove while scope from tree
                # scope_tree.remove_by_id(while_scope.scope_id)
                # # Get end of while scope
                # while_scope_end: Token = while_scope.scope_obj.classEnd
                # # Get while conditional
                # conditional_root_token = t.astOperand2

                # # Get code for true case
                # condition_true_root_tokens: List[Token] = []

                # cur_token: Token = while_scope.scope_obj.classStart
                # while root_tokens and cur_token.Id != while_scope_end.Id:
                #     if cur_token.Id == root_tokens[0].Id:
                #         condition_true_root_tokens.append(root_tokens.pop(0))

                #     cur_token = cur_token.next

                # # Parse true case
                # condition_true: List[Statement] = parse(condition_true_root_tokens, while_scope)

                # # Check backwards in scope for break/continue
                # break_continue_token = None
                # cur_token: Token = while_scope_end
                # while cur_token and cur_token.scopeId == while_scope_end.scopeId:
                #     if cur_token.str in ["break", "continue"]:
                #         break_continue_token = cur_token
                #         break  # Haha get it?

                #     cur_token = cur_token.previous

                # if break_continue_token:
                #     # Assumed that break/continue is always at the end of a statement
                #     condition_true.append(BlockStatement(break_continue_token))
                while_statement = self._parse_while(t, root_tokens, scope_tree)
                blocks.append(while_statement)
            # For statement
            elif t.astOperand1 and t.astOperand1.str == "for":
                # for_scope: ScopeNode = scope_tree.children[0]
                # assert for_scope.scope_obj.type == "For", f"Expected for scope, got {for_scope.scope_obj.type}"
                # scope_tree.remove_by_id(for_scope.scope_id)
                # for_scope_end: Token = for_scope.scope_obj.classEnd
                # conditional_root_token: Token = t.astOperand2

                # # Get code for true case
                # condition_true_root_tokens: List[Token] = []
                # cur_token: Token = for_scope.scope_obj.classStart
                # while root_tokens and cur_token.Id != for_scope_end.Id:
                #     if cur_token.Id == root_tokens[0].Id:
                #         condition_true_root_tokens.append(root_tokens.pop(0))

                #     cur_token = cur_token.next

                # condition_true: List[Statement] = parse(condition_true_root_tokens, for_scope)
                # for_statement = ForStatement(conditional_root_token, condition_true)

                # # Check backwards in scope for break/continue
                # break_continue_token = None
                # cur_token: Token = for_scope_end
                # while cur_token and cur_token.scopeId == for_scope_end.scopeId:
                #     if cur_token.str in ["break", "continue", "pass"]:
                #         break_continue_token = cur_token
                #         break  # Haha get it?

                #     cur_token = cur_token.previous

                # if break_continue_token:
                #     # Assumed that break/continue is always at the end of a statement
                #     condition_true.append(BlockStatement(break_continue_token))

                # # Convert for statement into while format
                # desugared_for = for_statement.desugar()
                # blocks.extend(desugared_for)
                desugared_for = self._parse_for(t, root_tokens, scope_tree).desugar()
                blocks.extend(desugared_for)
            # Switch statement
            elif t.astOperand1 and t.astOperand1.str == "switch":
                # # Grab swtich scope from tree
                # switch_scope: ScopeNode = scope_tree.children[0]
                # assert switch_scope.scope_obj.type == "Switch", f"Expected switch scope, got {switch_scope.scope_obj.type}"
                # # Remove switch scope from tree
                # scope_tree.remove_by_id(switch_scope.scope_id)
                # # Get end of switch scope
                # switch_scope_end: Token = switch_scope.scope_obj.classEnd
                # # Get while conditional
                # switch_expr_root_token: Token = t.astOperand2

                # # Get tokens for switch statment
                # switch_root_tokens: List[Statement] = []

                # cur_token: Token = switch_scope.scope_obj.classStart
                # while root_tokens and cur_token.Id != switch_scope_end.Id:
                #     if cur_token.Id == root_tokens[0].Id:
                #         switch_root_tokens.append(root_tokens.pop(0))

                #     cur_token = cur_token.next

                # # print([tokens_to_str(get_statement_tokens(x)) for x in switch_root_tokens])
                # # Get all case/default tokens
                # case_default_tokens = []
                # cur_token = t
                # while cur_token and cur_token.Id != switch_scope_end.Id:
                #     # print(cur_token.str)
                #     assert cur_token.str != "switch", "can't handle nested switch!"
                #     if cur_token.scopeId != switch_scope.scope_id:
                #         cur_token = cur_token.next
                #         continue
                #     if cur_token.str in ["case", "default"]:
                #         case_default_tokens.append(cur_token)

                #     cur_token = cur_token.next

                # # print([tokens_to_str(get_statement_tokens(x)) for x in case_default_tokens])

                # # Get all condition tokens
                # for i, cur_token in enumerate(case_default_tokens):
                #     match_case = None
                #     if cur_token.str == "case":
                #         match_case = cur_token.next if cur_token.next else None

                #     case_default_tokens[i] = (cur_token, match_case)

                # # Get all blocks of code in each case:
                # for i, (case_token, match_case) in enumerate(case_default_tokens):
                #     case_token_blocks = []

                #     next_case_token = switch_scope_end

                #     if i < len(case_default_tokens) - 1:
                #         next_case_token, _ = case_default_tokens[i + 1]

                #     while switch_root_tokens:
                #         cur_token = switch_root_tokens[0]

                #         if cur_token.Id >= next_case_token.Id:
                #             break

                #         case_token_blocks.append(cur_token)
                #         switch_root_tokens.pop(0)

                #     # print([tokens_to_str(get_statement_tokens(x)) for x in case_token_blocks])

                #     case_default_tokens[i] = (case_token, match_case, parse(case_token_blocks, switch_scope))

                # # Check backwards from each case statement to check for break/continue
                # for i in range(1, len(case_default_tokens) + 1):
                #     end_token = None
                #     if i == len(case_default_tokens):
                #         end_token = switch_scope_end
                #     else:
                #         end_token, _, _ = case_default_tokens[i]

                #     start_token, match_case, case_blocks = case_default_tokens[i - 1]

                #     cur_token = end_token
                #     break_continue_token = None
                #     while cur_token.Id >= start_token.Id:
                #         if cur_token.str in ["break", "continue", "pass"]:
                #             break_continue_token = cur_token
                #             break  # Haha get it?

                #         cur_token = cur_token.previous

                #     if break_continue_token:
                #         # Assumed that break/continue is always at the end of a statement
                #         case_blocks.append(BlockStatement(break_continue_token))
                #         case_default_tokens[i - 1] = (start_token, match_case, case_blocks)

                # # Make switch stmt objects
                # switch_blocks = []
                # for i, (case_token, match_case, case_blocks) in enumerate(case_default_tokens):
                #     case_token, match_case, case_blocks = case_default_tokens[i]
                #     switch_block = SwitchStatment(switch_expr_root_token, match_case, case_blocks)

                #     if case_token.str == "default":
                #         switch_block.is_default = True

                #     if case_blocks and case_blocks[-1].get_type() == "block":
                #         if case_blocks[-1].root_token.str in ["break", "continue", "pass"]:
                #             switch_block.has_break = True

                #     switch_blocks.append(switch_block)

                #     # Link together switch nodes
                #     if i == 0:
                #         pass
                #     else:
                #         previous = switch_blocks[i - 1]
                #         previous.next = switch_block
                #         switch_block.previous = previous

                # blocks.append(switch_blocks[0].desugar())
                switch_statement = self._parse_switch(t, root_tokens, scope_tree)
                blocks.append(switch_statement.desugar())
            # Regular statement
            else:
                blocks.append(BlockStatement(t))

        return blocks

    def _parse_if(self, if_token: Token, root_tokens: List[Token], scope_tree: ScopeNode) -> IfStatement:
        # print(f"Inside scope tree {scope_tree}")
        # Grab the scope from scope tree
        if_scope: ScopeNode = scope_tree.children[0]
        assert if_scope.scope_obj.type == "If", f"Expected if scope, got {if_scope.scope_obj.type}"
        # Remove scope from tree so it isn't reused
        scope_tree.remove_by_id(if_scope.scope_id)
        # Find end of scope (denoted by '}')
        if_scope_end: Token = if_scope.scope_obj.classEnd
        # Grab if statement conditional
        conditional_root_token = if_token.astOperand2

        # Get tokens for true case
        condition_true_root_tokens: List[Token] = []

        # Get tokens that are before the scope end
        cur_token: Token = if_scope.scope_obj.classStart
        while root_tokens and cur_token.Id != if_scope_end.Id:
            if cur_token.Id == root_tokens[0].Id:
                condition_true_root_tokens.append(root_tokens.pop(0))

            cur_token = cur_token.next

        # Recursively parse tokens
        condition_true: List[Statement] = parse(condition_true_root_tokens, if_scope)

        # Check backwards in scope for break/continue
        break_continue_token = None
        cur_token: Token = if_scope_end
        while cur_token and cur_token.scopeId == if_scope_end.scopeId:
            if cur_token.str in ["break", "continue"]:
                break_continue_token = cur_token
                break  # Haha get it?

            cur_token = cur_token.previous

        if break_continue_token:
            # Assumed that break/continue is always at the end of a statement
            condition_true.append(BlockStatement(break_continue_token))

        # Get tokens for false/else case
        condition_false_root_tokens: List[Token] = []
        condition_false: List[Statement] = []
        # Check if Else scope exists and directly follows If scope
        if scope_tree.children and scope_tree.children[0].scope_obj.type == "Else":
            else_scope: ScopeNode = scope_tree.children[0]
            else_scope_end: Token = else_scope.scope_obj.classEnd
            scope_tree.remove_by_id(if_scope.scope_id)

            condition_false_root_tokens: List[Token] = []

            cur_token: Token = else_scope.scope_obj.classStart
            while root_tokens and cur_token.Id != else_scope_end.Id:
                if cur_token.Id == root_tokens[0].Id:
                    condition_false_root_tokens.append(root_tokens.pop(0))

                cur_token = cur_token.next

            if condition_false_root_tokens:
                condition_false = parse(condition_false_root_tokens, else_scope)

            break_continue_token = None
            cur_token: Token = else_scope_end

            # Check backwards in scope for break/continue
            while cur_token and cur_token.scopeId == else_scope_end.scopeId:
                if cur_token.str in ["break", "continue"]:
                    break_continue_token = cur_token
                    break  # Haha get it?

                cur_token = cur_token.previous

            if break_continue_token:
                # Assumed that break/continue is always at the end of a statement
                condition_false.append(BlockStatement(break_continue_token))

        return IfStatement(conditional_root_token, condition_true, condition_false)

    def _parse_while(self, while_token: Token, root_tokens: List[Token], scope_tree: ScopeNode) -> WhileStatement:
        # Grab while scope from tree
        while_scope: ScopeNode = scope_tree.children[0]
        assert while_scope.scope_obj.type == "While", f"Expected while scope, got {while_scope.scope_obj.type}"
        # Remove while scope from tree
        scope_tree.remove_by_id(while_scope.scope_id)
        # Get end of while scope
        while_scope_end: Token = while_scope.scope_obj.classEnd
        # Get while conditional
        conditional_root_token = while_token.astOperand2

        # Get code for true case
        condition_true_root_tokens: List[Token] = []

        cur_token: Token = while_scope.scope_obj.classStart
        while root_tokens and cur_token.Id != while_scope_end.Id:
            if cur_token.Id == root_tokens[0].Id:
                condition_true_root_tokens.append(root_tokens.pop(0))

            cur_token = cur_token.next

        # Parse true case
        condition_true: List[Statement] = parse(condition_true_root_tokens, while_scope)

        # Check backwards in scope for break/continue
        break_continue_token = None
        cur_token: Token = while_scope_end
        while cur_token and cur_token.scopeId == while_scope_end.scopeId:
            if cur_token.str in ["break", "continue"]:
                break_continue_token = cur_token
                break  # Haha get it?

            cur_token = cur_token.previous

        if break_continue_token:
            # Assumed that break/continue is always at the end of a statement
            condition_true.append(BlockStatement(break_continue_token))

        return WhileStatement(conditional_root_token, condition_true)

    def _parse_for(self, for_token: Token, root_tokens: List[Token], scope_tree: ScopeNode) -> ForStatement:
        for_scope: ScopeNode = scope_tree.children[0]
        assert for_scope.scope_obj.type == "For", f"Expected for scope, got {for_scope.scope_obj.type}"
        scope_tree.remove_by_id(for_scope.scope_id)
        for_scope_end: Token = for_scope.scope_obj.classEnd
        conditional_root_token: Token = for_token.astOperand2

        # Get code for true case
        condition_true_root_tokens: List[Token] = []
        cur_token: Token = for_scope.scope_obj.classStart
        while root_tokens and cur_token.Id != for_scope_end.Id:
            if cur_token.Id == root_tokens[0].Id:
                condition_true_root_tokens.append(root_tokens.pop(0))

            cur_token = cur_token.next

        condition_true: List[Statement] = parse(condition_true_root_tokens, for_scope)
        for_statement = ForStatement(conditional_root_token, condition_true)

        # Check backwards in scope for break/continue
        break_continue_token = None
        cur_token: Token = for_scope_end
        while cur_token and cur_token.scopeId == for_scope_end.scopeId:
            if cur_token.str in ["break", "continue", "pass"]:
                break_continue_token = cur_token
                break  # Haha get it?

            cur_token = cur_token.previous

        if break_continue_token:
            # Assumed that break/continue is always at the end of a statement
            condition_true.append(BlockStatement(break_continue_token))

        return for_statement

    def _parse_switch(self, switch_statement: Token, root_tokens: List[Token], scope_tree: ScopeNode) -> SwitchStatment:
        # Grab swtich scope from tree
        switch_scope: ScopeNode = scope_tree.children[0]
        assert switch_scope.scope_obj.type == "Switch", f"Expected switch scope, got {switch_scope.scope_obj.type}"
        # Remove switch scope from tree
        scope_tree.remove_by_id(switch_scope.scope_id)
        # Get end of switch scope
        switch_scope_end: Token = switch_scope.scope_obj.classEnd
        # Get while conditional
        switch_expr_root_token: Token = switch_statement.astOperand2

        # Get tokens for switch statment
        switch_root_tokens: List[Statement] = []

        cur_token: Token = switch_scope.scope_obj.classStart
        while root_tokens and cur_token.Id != switch_scope_end.Id:
            if cur_token.Id == root_tokens[0].Id:
                switch_root_tokens.append(root_tokens.pop(0))

            cur_token = cur_token.next

        # print([tokens_to_str(get_statement_tokens(x)) for x in switch_root_tokens])
        # Get all case/default tokens
        case_default_tokens = []
        cur_token = switch_statement
        while cur_token and cur_token.Id != switch_scope_end.Id:
            # print(cur_token.str)
            assert cur_token.str != "switch", "can't handle nested switch!"
            if cur_token.scopeId != switch_scope.scope_id:
                cur_token = cur_token.next
                continue
            if cur_token.str in ["case", "default"]:
                case_default_tokens.append(cur_token)

            cur_token = cur_token.next

        # print([tokens_to_str(get_statement_tokens(x)) for x in case_default_tokens])

        # Get all condition tokens
        for i, cur_token in enumerate(case_default_tokens):
            match_case = None
            if cur_token.str == "case":
                match_case = cur_token.next if cur_token.next else None

            case_default_tokens[i] = (cur_token, match_case)

        # Get all blocks of code in each case:
        for i, (case_token, match_case) in enumerate(case_default_tokens):
            case_token_blocks = []

            next_case_token = switch_scope_end

            if i < len(case_default_tokens) - 1:
                next_case_token, _ = case_default_tokens[i + 1]

            while switch_root_tokens:
                cur_token = switch_root_tokens[0]

                if cur_token.Id >= next_case_token.Id:
                    break

                case_token_blocks.append(cur_token)
                switch_root_tokens.pop(0)

            # print([tokens_to_str(get_statement_tokens(x)) for x in case_token_blocks])

            case_default_tokens[i] = (case_token, match_case, parse(case_token_blocks, switch_scope))

        # Check backwards from each case statement to check for break/continue
        for i in range(1, len(case_default_tokens) + 1):
            end_token = None
            if i == len(case_default_tokens):
                end_token = switch_scope_end
            else:
                end_token, _, _ = case_default_tokens[i]

            start_token, match_case, case_blocks = case_default_tokens[i - 1]

            cur_token = end_token
            break_continue_token = None
            while cur_token.Id >= start_token.Id:
                if cur_token.str in ["break", "continue", "pass"]:
                    break_continue_token = cur_token
                    break  # Haha get it?

                cur_token = cur_token.previous

            if break_continue_token:
                # Assumed that break/continue is always at the end of a statement
                case_blocks.append(BlockStatement(break_continue_token))
                case_default_tokens[i - 1] = (start_token, match_case, case_blocks)

        # Make switch stmt objects
        switch_blocks = []
        for i, (case_token, match_case, case_blocks) in enumerate(case_default_tokens):
            case_token, match_case, case_blocks = case_default_tokens[i]
            switch_block = SwitchStatment(switch_expr_root_token, match_case, case_blocks)

            if case_token.str == "default":
                switch_block.is_default = True

            if case_blocks and case_blocks[-1].get_type() == "block":
                if case_blocks[-1].root_token.str in ["break", "continue", "pass"]:
                    switch_block.has_break = True

            switch_blocks.append(switch_block)

            # Link together switch nodes
            if i == 0:
                pass
            else:
                previous = switch_blocks[i - 1]
                previous.next = switch_block
                switch_block.previous = previous

        return switch_blocks[0]

    @staticmethod
    def write(function_declaration_objs: List[FunctionDeclaration], file_name: str, serialize_format="yaml"):
        """Serializes FunctionDeclaration objects to yaml/json"""
        objs_dict: List[Dict] = [f.to_dict() for f in function_declaration_objs]

        if serialize_format == "yaml":
            with open(file_name, "w", encoding="utf-8") as f:
                yaml.dump(objs_dict, f)
        elif serialize_format == "json":
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(objs_dict, f)
        else:
            raise ValueError("Format should be json or yaml")


def parse(root_tokens: List[Token], scope_tree: ScopeNode) -> List[Statement]:
    """Parses root tokens into AST Statement objects"""
    blocks: List[Statement] = []

    while root_tokens:
        t: Token = root_tokens.pop(0)


        # If block
        if t.astOperand1 and t.astOperand1.str == "if":
            # print(f"Inside scope tree {scope_tree}")
            # Grab the scope from scope tree
            if_scope: ScopeNode = scope_tree.children[0]
            assert if_scope.scope_obj.type == "If", f"Expected if scope, got {if_scope.scope_obj.type}"
            # Remove scope from tree so it isn't reused
            scope_tree.remove_by_id(if_scope.scope_id)
            # Find end of scope (denoted by '}')
            if_scope_end: Token = if_scope.scope_obj.classEnd
            # Grab if statement conditional
            conditional_root_token = t.astOperand2

            # Get tokens for true case
            condition_true_root_tokens: List[Token] = []

            # Get tokens that are before the scope end
            cur_token: Token = if_scope.scope_obj.classStart
            while root_tokens and cur_token.Id != if_scope_end.Id:
                if cur_token.Id == root_tokens[0].Id:
                    condition_true_root_tokens.append(root_tokens.pop(0))

                cur_token = cur_token.next

            # Recursively parse tokens
            condition_true: List[Statement] = parse(condition_true_root_tokens, if_scope)

            # Check backwards in scope for break/continue
            break_continue_token = None
            cur_token: Token = if_scope_end
            while cur_token and cur_token.scopeId == if_scope_end.scopeId:
                if cur_token.str in ["break", "continue"]:
                    break_continue_token = cur_token
                    break  # Haha get it?

                cur_token = cur_token.previous

            if break_continue_token:
                # Assumed that break/continue is always at the end of a statement
                condition_true.append(BlockStatement(break_continue_token))

            # Get tokens for false/else case
            condition_false_root_tokens: List[Token] = []
            condition_false: List[Statement] = []
            # Check if Else scope exists and directly follows If scope
            if scope_tree.children and scope_tree.children[0].scope_obj.type == "Else":
                else_scope: ScopeNode = scope_tree.children[0]
                else_scope_end: Token = else_scope.scope_obj.classEnd
                scope_tree.remove_by_id(if_scope.scope_id)

                condition_false_root_tokens: List[Token] = []

                cur_token: Token = else_scope.scope_obj.classStart
                while root_tokens and cur_token.Id != else_scope_end.Id:
                    if cur_token.Id == root_tokens[0].Id:
                        condition_false_root_tokens.append(root_tokens.pop(0))

                    cur_token = cur_token.next

                if condition_false_root_tokens:
                    condition_false = parse(condition_false_root_tokens, else_scope)

                break_continue_token = None
                cur_token: Token = else_scope_end

                # Check backwards in scope for break/continue
                while cur_token and cur_token.scopeId == else_scope_end.scopeId:
                    if cur_token.str in ["break", "continue"]:
                        break_continue_token = cur_token
                        break  # Haha get it?

                    cur_token = cur_token.previous

                if break_continue_token:
                    # Assumed that break/continue is always at the end of a statement
                    condition_false.append(BlockStatement(break_continue_token))

            blocks.append(IfStatement(conditional_root_token, condition_true, condition_false))
        # While statement
        elif t.astOperand1 and t.astOperand1.str == "while":
            # Grab while scope from tree
            while_scope: ScopeNode = scope_tree.children[0]
            assert while_scope.scope_obj.type == "While", f"Expected while scope, got {while_scope.scope_obj.type}"
            # Remove while scope from tree
            scope_tree.remove_by_id(while_scope.scope_id)
            # Get end of while scope
            while_scope_end: Token = while_scope.scope_obj.classEnd
            # Get while conditional
            conditional_root_token = t.astOperand2

            # Get code for true case
            condition_true_root_tokens: List[Token] = []

            cur_token: Token = while_scope.scope_obj.classStart
            while root_tokens and cur_token.Id != while_scope_end.Id:
                if cur_token.Id == root_tokens[0].Id:
                    condition_true_root_tokens.append(root_tokens.pop(0))

                cur_token = cur_token.next

            # Parse true case
            condition_true: List[Statement] = parse(condition_true_root_tokens, while_scope)

            # Check backwards in scope for break/continue
            break_continue_token = None
            cur_token: Token = while_scope_end
            while cur_token and cur_token.scopeId == while_scope_end.scopeId:
                if cur_token.str in ["break", "continue"]:
                    break_continue_token = cur_token
                    break  # Haha get it?

                cur_token = cur_token.previous

            if break_continue_token:
                # Assumed that break/continue is always at the end of a statement
                condition_true.append(BlockStatement(break_continue_token))

            blocks.append(WhileStatement(conditional_root_token, condition_true))
        # For statement
        elif t.astOperand1 and t.astOperand1.str == "for":
            for_scope: ScopeNode = scope_tree.children[0]
            assert for_scope.scope_obj.type == "For", f"Expected for scope, got {for_scope.scope_obj.type}"
            scope_tree.remove_by_id(for_scope.scope_id)
            for_scope_end: Token = for_scope.scope_obj.classEnd
            conditional_root_token: Token = t.astOperand2

            # Get code for true case
            condition_true_root_tokens: List[Token] = []
            cur_token: Token = for_scope.scope_obj.classStart
            while root_tokens and cur_token.Id != for_scope_end.Id:
                if cur_token.Id == root_tokens[0].Id:
                    condition_true_root_tokens.append(root_tokens.pop(0))

                cur_token = cur_token.next

            condition_true: List[Statement] = parse(condition_true_root_tokens, for_scope)
            for_statement = ForStatement(conditional_root_token, condition_true)

            # Check backwards in scope for break/continue
            break_continue_token = None
            cur_token: Token = for_scope_end
            while cur_token and cur_token.scopeId == for_scope_end.scopeId:
                if cur_token.str in ["break", "continue", "pass"]:
                    break_continue_token = cur_token
                    break  # Haha get it?

                cur_token = cur_token.previous

            if break_continue_token:
                # Assumed that break/continue is always at the end of a statement
                condition_true.append(BlockStatement(break_continue_token))

            # Convert for statement into while format
            desugared_for = for_statement.desugar()
            blocks.extend(desugared_for)
        # Switch statement
        elif t.astOperand1 and t.astOperand1.str == "switch":
            # Grab swtich scope from tree
            switch_scope: ScopeNode = scope_tree.children[0]
            assert switch_scope.scope_obj.type == "Switch", f"Expected switch scope, got {switch_scope.scope_obj.type}"
            # Remove switch scope from tree
            scope_tree.remove_by_id(switch_scope.scope_id)
            # Get end of switch scope
            switch_scope_end: Token = switch_scope.scope_obj.classEnd
            # Get while conditional
            switch_expr_root_token: Token = t.astOperand2

            # Get tokens for switch statment
            switch_root_tokens: List[Statement] = []

            cur_token: Token = switch_scope.scope_obj.classStart
            while root_tokens and cur_token.Id != switch_scope_end.Id:
                if cur_token.Id == root_tokens[0].Id:
                    switch_root_tokens.append(root_tokens.pop(0))

                cur_token = cur_token.next

            # print([tokens_to_str(get_statement_tokens(x)) for x in switch_root_tokens])
            # Get all case/default tokens
            case_default_tokens = []
            cur_token = t
            while cur_token and cur_token.Id != switch_scope_end.Id:
                # print(cur_token.str)
                assert cur_token.str != "switch", "can't handle nested switch!"
                if cur_token.scopeId != switch_scope.scope_id:
                    cur_token = cur_token.next
                    continue
                if cur_token.str in ["case", "default"]:
                    case_default_tokens.append(cur_token)

                cur_token = cur_token.next

            # print([tokens_to_str(get_statement_tokens(x)) for x in case_default_tokens])

            # Get all condition tokens
            for i, cur_token in enumerate(case_default_tokens):
                match_case = None
                if cur_token.str == "case":
                    match_case = cur_token.next if cur_token.next else None

                case_default_tokens[i] = (cur_token, match_case)

            # Get all blocks of code in each case:
            for i, (case_token, match_case) in enumerate(case_default_tokens):
                case_token_blocks = []

                next_case_token = switch_scope_end

                if i < len(case_default_tokens) - 1:
                    next_case_token, _ = case_default_tokens[i + 1]

                while switch_root_tokens:
                    cur_token = switch_root_tokens[0]

                    if cur_token.Id >= next_case_token.Id:
                        break

                    case_token_blocks.append(cur_token)
                    switch_root_tokens.pop(0)

                # print([tokens_to_str(get_statement_tokens(x)) for x in case_token_blocks])

                case_default_tokens[i] = (case_token, match_case, parse(case_token_blocks, switch_scope))

            # Check backwards from each case statement to check for break/continue
            for i in range(1, len(case_default_tokens) + 1):
                end_token = None
                if i == len(case_default_tokens):
                    end_token = switch_scope_end
                else:
                    end_token, _, _ = case_default_tokens[i]

                start_token, match_case, case_blocks = case_default_tokens[i - 1]

                cur_token = end_token
                break_continue_token = None
                while cur_token.Id >= start_token.Id:
                    if cur_token.str in ["break", "continue", "pass"]:
                        break_continue_token = cur_token
                        break  # Haha get it?

                    cur_token = cur_token.previous

                if break_continue_token:
                    # Assumed that break/continue is always at the end of a statement
                    case_blocks.append(BlockStatement(break_continue_token))
                    case_default_tokens[i - 1] = (start_token, match_case, case_blocks)

            # Make switch stmt objects
            switch_blocks = []
            for i, (case_token, match_case, case_blocks) in enumerate(case_default_tokens):
                case_token, match_case, case_blocks = case_default_tokens[i]
                switch_block = SwitchStatment(switch_expr_root_token, match_case, case_blocks)

                if case_token.str == "default":
                    switch_block.is_default = True

                if case_blocks and case_blocks[-1].get_type() == "block":
                    if case_blocks[-1].root_token.str in ["break", "continue", "pass"]:
                        switch_block.has_break = True

                switch_blocks.append(switch_block)

                # Link together switch nodes
                if i == 0:
                    pass
                else:
                    previous = switch_blocks[i - 1]
                    previous.next = switch_block
                    switch_block.previous = previous

            blocks.append(switch_blocks[0].desugar())
        # Regular statement
        else:
            blocks.append(BlockStatement(t))

    return blocks


def print_AST(function_body):
    for b in function_body:
        print("_____")
        if b.get_type() == "block":
            print(tokens_to_str(get_statement_tokens(b.root_token)))
        elif b.get_type() == "if":
            print("IF:")
            print(tokens_to_str(get_statement_tokens(b.condition)))
            print("IF TRUE:")
            print_AST(b.condition_true)
            print("END TRUE")
            print("IF FALSE:")
            print_AST(b.condition_false)
            print("END FALSE")
            print("END IF")
        elif b.get_type() == "while":
            print("WHILE:")
            print(tokens_to_str(get_statement_tokens(b.condition)))
            print("IF TRUE:")
            print_AST(b.condition_true)
            print("END TRUE")
            print("END WHILE")
        elif b.get_type() == "for":
            print("FOR:")
            print(tokens_to_str(get_statement_tokens(b.condition)))
            print("DO:")
            print_AST(b.condition_true)
        elif b.get_type() == "switch":
            if b.is_default:
                print(f"SWITCH: (default = {b.is_default})")
            else:
                print(f"SWITCH: {b.switch_expr.str} == {b.match_expr.str} (default = {b.is_default})")
            print_AST(b.match_true)
            if b.next:
                print_AST([b.next])

def main():
    # test_path = "/home/rewong/phys/ryan/control_flow/dump_to_ast_test/test_19.cpp.dump"
    # test_path = "/home/rewong//phys/data/jaguar_base/src/motor_and_sensors_controller.cpp.dump"
    test_path = "/home/rewong/phys/data/FrenchVanilla/src/turtlebot_example/src/turtlebot_example_node.cpp.dump"
    dumper = DumpToAST(test_path)
    parsed = dumper.convert()
    print_AST(parsed[0].body)
    # print([x.scope_obj.type for x in parsed[0].scope_tree.children])

    # cur = [parsed[0].scope_tree]
    # while cur:
    #     x = cur.pop(0)
    #     print(x.scope_id)
    #     print([z.scope_id for z in x.children])
    #     cur.extend(x.children)

    # print_AST(parsed[0].body)
    # DumpToAST.write(parsed, "test_9.yaml")
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

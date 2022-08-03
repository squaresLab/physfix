"""Tree based data structure for keeping track of scopes"""
from __future__ import annotations

from typing import List, Union

from cpp_parser import Scope, Configuration


class ScopeNode:
    """Node for a tree of Scopes"""
    def __init__(self, scope_obj: Scope):
        self.scope_id: str = scope_obj.Id
        self.scope_obj: Scope = scope_obj
        self.children: List[ScopeNode] = []
        self.parent: Union[ScopeNode, None] = None

    def remove_by_id(self, scope_id: str) -> bool:
        """Remove subtree where the root has Id == scope_id
        by scope ID

        Returns:
            bool : Whether the node was removed
        """
        for i, children in enumerate(self.children):
            if children.scope_id == scope_id:
                self.children.pop(i)
                return True

            res = children.remove_by_id(scope_id)
            if res:
                return True

        return False

    def find_by_id(self, scope_id: str) -> Union[ScopeNode, None]:
        """Finds node by scope_id"""
        if scope_id == self.scope_id:
            return self

        for node in self.children:
            res = node.find_by_id(scope_id)

            if res:
                return res

        return None

    def find_by_obj(self, scope_obj: Scope) -> Union[ScopeNode, None]:
        """Finds node by scope_obj"""
        return self.find_by_id(scope_obj.Id)

    @staticmethod
    def make_scope_tree(cppcheck_config: Configuration, scope_obj: Scope):
        """Creates a scope tree using scopes in cppcheck_config where the
        root is the scope_obj
        """
        if not scope_obj:
            return None

        scope_node: ScopeNode = ScopeNode(scope_obj)
        scope_children: List[ScopeNode] = []
        # Find nested children
        for i, s in enumerate(cppcheck_config.scopes):
            if s == scope_node.scope_obj:
                continue

            # Remove try scopes and change the "Else" scope to have the "Try" scope_id
            if s.type == "Else":
                s.Id = cppcheck_config.scopes[i + 1].Id
                cppcheck_config.scopes[i + 1].nestedInId = "-1"

            # If a scope is nested inside of the root node (is a child of root)
            if s.nestedInId == scope_node.scope_id:
                # Recurse
                scope_node_child = ScopeNode.make_scope_tree(cppcheck_config, s)
                if scope_node_child:
                    scope_node_child.parent = scope_obj
                    scope_children.append(scope_node_child)

        scope_node.children = scope_children
        return scope_node

    def copy(self) -> ScopeNode:
        """Creates a deep copy of self"""
        scope_node_copy = ScopeNode(self.scope_obj)

        if scope_node_copy.parent is not None:
            scope_node_copy.parent = self.parent.copy()
        copy_children = []

        for node in self.children:
            copy_children.append(node.copy())
        scope_node_copy.children = copy_children

        return scope_node_copy

    def __repr__(self):
        scope_tree_dict = {"type": self.scope_obj.type}
        scope_tree_dict[self.scope_id] = []

        for c in self.children:
            scope_tree_dict[self.scope_id].append(repr(c))

        return str(scope_tree_dict)
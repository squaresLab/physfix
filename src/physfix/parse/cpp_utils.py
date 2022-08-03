from typing import Dict, List, Set, Union

from .cpp_parser import Configuration, Scope, Token, Variable


def get_statement_tokens(token: Token) -> List[Token]:
    """Returns tokens in token tree in inorder"""
    if not token:
        return []
    elif not(token.astOperand1 or token.astOperand2):
        return [token]

    return get_statement_tokens(token.astOperand1) + [token] + get_statement_tokens(token.astOperand2)


def get_vars_from_statement(tokens: List[Token]) -> List[Variable]:
    """Returns all tokens in a list of tokens which represent a variable"""
    variables = []
    for t in tokens:
        if t.variable:
            variables.append(t.variable)

    return variables


def get_lhs_from_statement(tokens: List[Token]) -> List[Token]:
    """Returns the tokens of the LHS of an expression"""
    for idx, t in enumerate(tokens):
        if "=" == t.str:
            return tokens[:idx]


def get_rhs_from_statement(tokens: List[Token]) -> List[Token]:
    """
    Returns the tokens of the RHS of an expression
    """
    for idx, t in enumerate(tokens):
        if "=" == t.str:
            return tokens[idx:]


def tokens_to_str(tokens: List[Token]) -> List[str]:
    """Returns a list of strings extracted from a list of tokens"""
    return list(map(lambda x: x.str, tokens))


def token_to_stmt_str(t: Token) -> List[str]:
    """Traverses token in inorder and returns a list of strings"""
    return tokens_to_str(get_statement_tokens(t))


def get_root_token(t: Token) -> Token:
    """Returns the root of a token tree"""
    while t.astParent:
        t = t.astParent

    return t


def get_root_tokens(token_start: Token, token_end: Token) -> List[Token]:
    """ Takes the start and end tokens for a function and finds the root tokens
    of all statments in the function.
    """
    root_tokens_set: Set[Token] = set()
    root_tokens = []
    current_token: Union[Token, None] = token_start

    while current_token is not None and current_token != token_end:  #todo: reverse token set exploration to top-down instead of bottom-up
        # HAS A PARENT
        if current_token.astParent: 
            token_parent = current_token.astParent
            has_parent = True
            while has_parent:
                # HAS NO PARENT, THEREFORE IS ROOT
                if not token_parent.astParent:
                    if token_parent not in root_tokens_set:
                        root_tokens_set.add(token_parent)
                        root_tokens.append(token_parent)
                    token_parent.isRoot = True  # THIS PROPERTY IS A CUSTOM NEW PROPERTY
                    has_parent = False
                else:
                    token_parent = token_parent.astParent
        current_token = current_token.next

    # root_tokens = list(root_tokens_set)
    # SORT NUMERICALLY BY LINE NUMBER
    # root_tokens = sorted(root_tokens, key=lambda x: int(x.linenr))
    return root_tokens


# This is needed since not all tokens in a statment are children of the root token for some reason
def get_function_statements(start_token: Token, end_token: Token, root_tokens: List[Token]) -> List[List[Token]]:
    """Takes the start and end tokens of a function and a list of the root tokens
    of the statments in a funciton and returns all of the tokens of each statment.
    """
    function_statements = [get_statement_tokens(t) for t in root_tokens]

    for i, statement in enumerate(function_statements):
        cur = statement[-1].next
        statement_end = None

        if i == len(function_statements) - 1:
            statement_end = end_token.previous
        else:
            statement_end = function_statements[i + 1][0]

        while cur and cur != statement_end:
            statement.append(cur)
            cur = cur.next

    return function_statements


def get_functions(cppcheck_config: Configuration) -> Dict[str, Dict]:
    """Retrieves function information from Cppcheck Config obj."""
    function_dicts: Dict[str, Dict] = {}

    # FIND FUNCTIONS IN "SCOPES" REGION OF DUMP FILE, START AND END TOKENs
    for s in cppcheck_config.scopes:
        if s.type == "Function":
            # SCAN ALL FUNCTIONS UNLESS LIST OF FUNCTIONS SPECIFIED
            function_dicts[s.Id] = {"name": s.className,
                                    "linern": s.classStart.linenr,
                                    "token_start": s.classStart,
                                    "token_end": s.classEnd,
                                    "scopeObject": s,
                                    "scopes": [],
                                    "symbol_table": {},
                                    "function_graph_edges": [],
                                    "function": s.function}
            # CONSTRUCT LIST OF ROOT TOKENS
            function_dicts[s.Id]["root_tokens"] = get_root_tokens(s.classStart, s.classEnd)

    return function_dicts


def get_function_scopes(cppcheck_config: Configuration, function_scope_id: str) -> List[Scope]:
    """Takes a function and returns a list of scopes nested within that function.
    """
    nested_scopes: List[Scope] = []
    for s in cppcheck_config.scopes:
        if s.nestedIn == function_scope_id:
            nested_scopes.append(s)

    return nested_scopes

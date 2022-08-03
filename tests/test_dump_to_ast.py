import unittest
import yaml
from yaml.loader import SafeLoader
import os
import sys

# from physfix import parse.dump_to_ast.DumpToAST
from ..parse.dump_to_ast import DumpToAST
# from phys import physfix
# from ...parse.dump_to_ast import DumpToAST
from physfix.parse.cpp_utils import token_to_stmt_str

# phys
# |
# +-- physfix/
#      |
#      +-- __init__.py
#      |
#      +-- tests/
#      |    |
#      |    +-- test_dump_to_ast.py
#      |
#      +-- parse/
#           |
#           +-- __init__.py
#           |
#           +-- dump_to_ast.py


class TestDumpToAST(unittest.TestCase):
    """Tests the DumpToAST class"""
    def test(self):
        for i in range(1, 15):
            test_path = f"./dump_to_ast_test/test_{i}.cpp.dump"
            sol_path = f"./dump_to_ast_test/test_{i}_solution.yaml"
            ast_converter = DumpToAST(test_path)
            ast = ast_converter.convert()
            ast_dict = [f.to_dict() for f in ast]

            sol_dict = None
            with open(sol_path) as f:
                sol_dict = yaml.load(f, Loader=SafeLoader)

            self.assertEqual(ast_dict, sol_dict)

if __name__ == "__main__":
    unittest.main()
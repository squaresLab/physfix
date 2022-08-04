import os
import unittest

import yaml
from physfix.parse.dump_to_ast import DumpToAST
from yaml.loader import SafeLoader

DIR_HERE = os.path.dirname(__file__)

class TestDumpToAST(unittest.TestCase):
    """Tests the DumpToAST class"""
    def test(self):
        for i in range(1, 15):
            test_path = os.path.join(DIR_HERE, "dump_to_ast_test", f"test_{i}.cpp.dump")
            sol_path = os.path.join(DIR_HERE, "dump_to_ast_test", f"test_{i}_solution.yaml")

            dump_to_ast = DumpToAST(test_path)
            ast = dump_to_ast.convert()
            ast_dict = [f.to_dict() for f in ast]

            sol_dict = None
            with open(sol_path) as f:
                sol_dict = yaml.load(f, Loader=SafeLoader)

            self.assertEqual(ast_dict, sol_dict)

if __name__ == "__main__":
    unittest.main()

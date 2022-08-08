import os
import unittest

import yaml
from physfix.dataflow.ast_to_cfg import ASTToCFG
from physfix.dataflow.dependency_graph import CFGToDependencyGraph
from physfix.parse.dump_to_ast import DumpToAST
from yaml.loader import SafeLoader

DIR_HERE = os.path.dirname(__file__)

class TestCFGToDependencyGraph(unittest.TestCase):
    def test(self):
        for i in range(1, 3):
            print(f"=====Testing {i}=====")
            test_path = os.path.join(DIR_HERE, "data_dependency_test", f"test_{i}.cpp.dump")
            sol_path = os.path.join(DIR_HERE, "data_dependency_test", f"test_{i}_solution.yaml")

            dump_to_ast = DumpToAST(test_path)
            ast_to_cfg = ASTToCFG(dump_to_ast)
            cfg_to_dependency_graph_1 = CFGToDependencyGraph(ast_to_cfg)
            dependency_graph = cfg_to_dependency_graph_1.convert()[0]
            graph_dict = dependency_graph.to_dict()

            # Making sure that .to_dict returns same thing each time
            cfg_to_dependency_graph_2 = CFGToDependencyGraph(ast_to_cfg)
            dependency_graph2 = cfg_to_dependency_graph_2.convert()[0]
            graph_dict_2 = dependency_graph2.to_dict()

            self.assertEqual(graph_dict, graph_dict_2)

            sol_dict = None
            with open(sol_path) as f:
                sol_dict = yaml.load(f, Loader=SafeLoader)

            self.assertEqual(graph_dict, sol_dict)

    # def compare_inputs(self, d1, d2):
    #     if isinstance(d1, str):
    #         self.assertEqual(d1, d2)
    #     elif isinstance(input, list):
    #         self.assertTrue(isinstance(d2, list))
    #         for i in d1:
    #             self.asserTrue(i in d1)
    #     elif isinstance(input, dict):
    #         self.assertTrue(isinstance(d2, dict))
    #         self.assertEqual(len(d1), len(d2))
    #         for k, v in d1.items():
    #             self.assertTrue(k in d2)
    #             self.compare_inputs(v, d2[k])
                

if __name__ == "__main__":
    unittest.main()

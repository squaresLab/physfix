import unittest
import yaml
from yaml.loader import SafeLoader
from physfix.src.physfix.ast_to_cfg import ASTToCFG
from dependency_graph import CFGToDependencyGraph, DependencyGraph


class TestCFGToDependencyGraph(unittest.TestCase):
    def test(self):
        for i in range(1, 3):
            print(f"=====Testing {i}=====")
            test_path = f"./data_dependency_test/test_{i}.cpp.dump"
            sol_path = f"./data_dependency_test/test_{i}_solution.yaml"
            cfg = ASTToCFG.convert(test_path)[0]
            dependency_graph = CFGToDependencyGraph.create_dependency_graph(cfg)
            graph_dict = dependency_graph.to_dict()

            # Making sure that .to_dict returns same thing each time
            dependency_graph2 = CFGToDependencyGraph.create_dependency_graph(cfg)
            graph_dict2 = dependency_graph2.to_dict()

            self.assertEqual(graph_dict, graph_dict2)

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
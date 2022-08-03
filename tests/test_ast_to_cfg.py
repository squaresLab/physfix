import unittest
import yaml
from yaml.loader import SafeLoader
from ast_to_cfg import ASTToCFG

class TestASTToCFG(unittest.TestCase):
    def test(self):
        for i in range(1, 15):
            print(f"=====Testing {i}=====")
            test_path = f"./ast_to_cfg_test/test_{i}.cpp.dump"
            sol_path = f"./ast_to_cfg_test/test_{i}_solution.yaml"
            cfg = ASTToCFG.convert(test_path)
            cfg_dict = [f.to_dict() for f in cfg]

            # Making sure that .to_dict returns same thing each time
            cfg2 = ASTToCFG.convert(test_path)
            cfg_dict2 = [f.to_dict() for f in cfg2]

            # print(cfg_dict)
            # print(cfg_dict2)
            self.assertEqual(cfg_dict, cfg_dict2)

            sol_dict = None
            with open(sol_path) as f:
                sol_dict = yaml.load(f, Loader=SafeLoader)
            
            for k, v in cfg_dict[0].items():
                print("____")
                print(k)
                print("Code solution")
                print(v)
                print("Written solution")
                print(sol_dict[0][k])
            self.assertEqual(cfg_dict, sol_dict)
            # self.compare_inputs(cfg_dict, sol_dict)

    def compare_inputs(self, d1, d2):
        if isinstance(d1, str):
            self.assertEqual(d1, d2)
        elif isinstance(input, list):
            self.assertTrue(isinstance(d2, list))
            for i in d1:
                self.asserTrue(i in d1)
        elif isinstance(input, dict):
            self.assertTrue(isinstance(d2, dict))
            self.assertEqual(len(d1), len(d2))
            for k, v in d1.items():
                self.assertTrue(k in d2)
                self.compare_inputs(v, d2[k])
                

if __name__ == "__main__":
    unittest.main()
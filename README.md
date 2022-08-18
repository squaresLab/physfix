# PhysFix - Automatically fixing unit inconsistencies for ROS C++

PhysFix workflow:
1. Run Phys on C++ files. Generate tokens xml, json with errors and variable units
2. Parse the tokens xml into an AST
3. Convert the AST into a CFG
4. Create dependency/dataflow graph from CFG
5. Generate changes for errors using in-scope variables
6. Parse C++ file into XML using srcML
7. Convert changes into XSLT files
8. Apply XSLT file to srcML XML file

## Files/Folders
| File/Folder | Purpose |
|-------------|---------|
| /extern/phys | Link to squaresLab fork of Phys as a git submodule |
| /test | Folder with test files |
| /src | Relevant physfix source files are here |
| /src/physfix/parse | Folder with files that turn tokens XML into dependency graph |
| /src/physfix/parse/cpp_parser.py | Converts tokens XML into python classes. Copied from Phys repo |
| /src/physfix/parse/cpp_utils.py | Utilities for working with classes from cpp_parser.py |
| /src/physfix/parse/dump_to_ast.py | Converts classes from cpp_parser.py into real AST |
| /src/physfix/parse/scope_node.py | Helper class for dump_to_ast.py. Keeps tracks of scopes in a tree-like data structure |
| /src/physfix/parse/statement.py | Data classes for AST |
| /src/physfix/dataflow/ast_to_cfg.py | Converts ast into control flow graph |
| /src/physfix/dataflow/cfg_node.py | Data classes for CFG |
| /src/physfix/dataflow/reach_def.py | Finds definition-use pairs and reaching definitions from CFG |
| /src/physfix/dataflow/dependency_graph.py | Converts CFG into dependency graph |
| /src/physfix/phys_fix.py | Class with end-to-end pipeline, has code for reading/writing xml/xslt files |
| /src/physfix/run_phys.sh | Helper bash script to run phys using docker |


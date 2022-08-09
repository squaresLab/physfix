from __future__ import annotations

import os
import shutil
import subprocess
from collections import deque

from lxml import etree

from physfix.parse.dump_to_ast import DumpToAST
from physfix.dataflow.ast_to_cfg import ASTToCFG
from physfix.dataflow.dependency_graph import CFGToDependencyGraph
from physfix.error_fix.fix_addition_subtraction import fix_addition_subtraction
from physfix.error_fix.phys_fix_utils import (Change, Error, PhysVar,
                                              get_error_dependency_node,
                                              get_token_unit_map)
from physfix.parse.cpp_parser import CppcheckData
from physfix.parse.cpp_utils import get_root_token, get_statement_tokens

DIR_HERE = os.path.dirname(__file__)

class PhysFix:
    """Full pipeline for fixing unit inconsistencies in Phys"""
    def __init__(self, source_file_path: str):
        self.source_file_name = os.path.basename(source_file_path)
        self.physfix_folder = os.path.join(DIR_HERE, "data")

        # Copy source file into new folder
        self.source_file_path = os.path.join(self.physfix_folder,
                                             os.path.splitext(self.source_file_name)[0],
                                             self.source_file_name)

        if not os.path.exists(os.path.dirname(self.source_file_path)):
            os.makedirs(os.path.dirname(self.source_file_path))

        shutil.copy(source_file_path, self.source_file_path)

        self.source_directory = os.path.dirname(self.source_file_path)

    def run_phys(self, mount_path: str, file_path: str, output_path: str):
        """Runs Phys on a file"""
        subprocess.run([os.path.join(DIR_HERE, "run_phys.sh"), mount_path, file_path, output_path])

    def run_source_ml(self, file_path: str, ouput_path: str):
        """Runs srcml on a file"""
        subprocess.run(["srcml", "--position", file_path, "-o", ouput_path])

    def fix(self):
        phys_output_path = os.path.join(self.source_directory,
                                        f"{os.path.splitext(self.source_file_name)[0]}.json")

        if not os.path.exists(phys_output_path):
            with open(phys_output_path, "w") as _:
                pass

        self.run_phys(os.path.dirname(self.source_file_path), self.source_file_path, phys_output_path)
        
        # Get AST/CFG/DependencyGraph
        dump_to_ast = DumpToAST(f"{self.source_file_path}.dump")
        dump_to_ast.convert()
        ast_to_cfg = ASTToCFG(dump_to_ast)
        ast_to_cfg.convert()
        cfg_to_dependency = CFGToDependencyGraph(ast_to_cfg)
        cfg_to_dependency.convert()
        dependency_graph = cfg_to_dependency.dependency_graph

        # Get errors arbitrarily for now (and only addition/subtraction)
        phys_errors = [e for e in Error.from_dict(phys_output_path) if e.error_type == "ADDITION_OF_INCOMPATIBLE_UNITS"]
        
        if not phys_errors:
            return

        phys_vars = PhysVar.from_dict(phys_output_path)
        var_unit_map = PhysVar.create_unit_map(phys_vars)
        token_unit_map = get_token_unit_map(phys_output_path)
        # Currently only fix one bug for now
        get_error_dependency_node(phys_errors[0], dependency_graph)
        change = fix_addition_subtraction(phys_errors[0], var_unit_map, token_unit_map)

        # Get srcml file
        srcml_output_path = os.path.join(self.source_directory,
                                         f"{os.path.splitext(self.source_file_name)[0]}.xml")
        self.run_source_ml(self.source_file_path, srcml_output_path)
        srcml_xml = self.load_srcml_xml(srcml_output_path, strip_namespace=True)

        # Create XLST files
        xslt_output_prefix = os.path.join(self.source_directory, f"{self.source_file_name}_patch")
        self.changes_to_xslt(srcml_xml, change, xslt_output_prefix)
        
    def load_srcml_xml(self, xml_path, strip_namespace=False):
        it = etree.parse(xml_path)

        if strip_namespace:
            self._stripNs(it.getroot())
        return it

    def _stripNs(self, el):
        '''Recursively search this element tree, removing namespaces.'''
        if el.tag.startswith("{"):
            el.tag = el.tag.split('}', 1)[1]  # strip namespace
        keys = list(el.attrib.keys())
        for k in keys:
            if k.startswith("{"):
                k2 = k.split('}', 1)[1]
                el.attrib[k2] = el.attrib[k]
                del el.attrib[k]
        for child in el:
            self._stripNs(child)

    def root_token_to_xml(self, token):
        """Takes root token and turns it into xml elements"""
        if not token:
            return []

        # print("_____")
        # print(f"Currently: {tokens_to_str([token])}")
        # if token.astOperand1:
        #     print(f"left: {tokens_to_str([token.astOperand1])}")
        # if token.astOperand2:
        #     print(f"right: {tokens_to_str([token.astOperand2])}")

        xml_elems = []
        if token.variableId:
            elem = etree.Element("name")
            elem.text = token.str
            return [elem]
        else:
            if token.str in "*/+-":
                elem = etree.Element("operator")
                elem.text = token.str
                mid = [elem]
                left = self.root_token_to_xml(token.astOperand1)
                right = self.root_token_to_xml(token.astOperand2)
                xml_elems = left + mid + right
            elif token.str == "(":
                left = etree.Element("call")
                left = etree.SubElement(left, "name")
                left.text = token.astOperand1.str
                mid = etree.SubElement(left, "argument_list")
                mid.text = "("
                mid.tail = ")"
                
                cur = token.astOperand2
                while cur and cur.str == ",":
                    arg = etree.SubElement(mid, "argument")
                    arg.tail = ","
                    arg = etree.SubElement(arg, "expr")
                    arg = arg.extend(self.root_token_to_xml(cur.astOperand1))

                    cur = cur.astOperand2

                if cur:
                    arg = etree.SubElement(mid, "argument")
                    arg = etree.SubElement(arg, "expr")
                    arg = arg.extend(self.root_token_to_xml(cur))

                xml_elems.append(left)
            else:
                mid = [etree.Element("literal")]
                mid[0].text = token.str
                left = self.root_token_to_xml(token.astOperand1)
                right = self.root_token_to_xml(token.astOperand2)
                xml_elems = left + mid + right

        return xml_elems

    def changes_to_xslt(self, srcml_xml, change: Change, output_file_prefix):
        srcml_xml_root = srcml_xml.getroot()
        token_to_fix = change.token_to_fix
        token_to_fix_root = get_root_token(token_to_fix)
        statement_tokens = get_statement_tokens(token_to_fix_root)
        token_line_num = token_to_fix_root.linenr
        exprs = srcml_xml_root.findall(".//expr")
        line_elem = []

        # Find the xml line with the matching line number
        for e in exprs:
            if e.get("start").startswith(str(token_line_num)):
                line_elem.append(e)

        cur_token = statement_tokens[0]

        elem_to_fix = None
        elem_parent_map = {}
        # Find the token to replace in the xml
        for e_idx, e in enumerate(line_elem):
            q = deque()
            q.append((e_idx, e))

            elem_found = False
            while q:
                idx, cur = q.popleft()

                if cur.text:
                    assert cur.text == cur_token.str, "Text not matching"
                    if cur_token.Id == token_to_fix.Id:
                        elem_found = True
                        elem_to_fix = cur
                        break

                    cur_token = cur_token.next

                for next_elem in cur:
                    elem_parent_map[next_elem] = cur
                    q.append((idx, next_elem))
            
            if elem_found:
                break
        
        if elem_to_fix.text == "(":
            elem_to_fix = elem_parent_map[elem_to_fix]

        change_xml_elems = [self.root_token_to_xml(c) for c in change.changes]

        for idx, change_sub_elem in enumerate(change_xml_elems):
            print(idx)
            xslt_root = etree.XML('''<?xml version = "1.0"?>
    <xsl:stylesheet version = "1.0" 
    xmlns:xsl = "http://www.w3.org/1999/XSL/Transform">
        <xsl:template match="@*|node()">
            <xsl:copy>
                <xsl:apply-templates select="@*|node()"/>
            </xsl:copy>
        </xsl:template>
    </xsl:stylesheet>''')
            xslt_tree = etree.ElementTree(xslt_root)
            xslt_match = etree.SubElement(xslt_tree.getroot(), "{http://www.w3.org/1999/XSL/Transform}template",
                                          match=f"//{elem_to_fix.tag}[@start='{elem_to_fix.get('start')}'][@end='{elem_to_fix.get('end')}']")
            xslt_match.extend(change_sub_elem)
            xslt_tree.write(f"{output_file_prefix}_{idx}.xml")

    @staticmethod
    def apply_xslt(srcml_xml, xslt, output_path):
        transform = etree.XSLT(xslt)
        t = transform(srcml_xml)

        with open(f"{output_path}.xml", "wb") as f:
            f.write(etree.tostring(t))
        
        with open(f"{output_path}.cpp", "wb") as f:
            f.write(etree.tostring(t, method='text'))

    


def main():
    phys_fix = PhysFix("/home/rewong/phys/physfix/tests/dump_to_ast_test/test_19.cpp")
    phys_fix.fix()
    # output = "/home/rewong/phys/src/test_19_output.json"
    # dump = "/home/rewong/phys/physfix/tests/dump_to_ast_test/test_19.cpp.dump"

    # cppconfig = CppcheckData(dump).configurations[0]
    # cfgs = ASTToCFG().convert(dump)
    # d_graphs = [CFGToDependencyGraph().create_dependency_graph(c) for c in cfgs]

    # e = Error.from_dict(output)
    # # print(e)
    # e_dependency = get_error_dependency_node(e[0], d_graphs)
    # phys_vars = PhysVar.from_dict(output)
    # var_unit_map = PhysVar.create_unit_map(phys_vars)
    # token_unit_map = get_token_unit_map(output)
    # changes = fix_addition_subtraction(e[0], var_unit_map, token_unit_map)
    # cfgs = ASTToCFG().convert(dump)
    # d_graphs = [CFGToDependencyGraph().create_dependency_graph(c) for c in cfgs]

    # e = Error.from_dict(phys_output)
    # print(e)
    # e_dependency = get_error_dependency_node(e[0], d_graphs)
    # print(d_graphs[0])
    # print(d_graphs[0].get_node_connected_components(e_dependency[1]))

    # x = PhysFix.load_srcml_xml("/home/rewong/phys/physfix/test_src_ml.xml",
    # strip_namespace=True)
    # PhysFix.changes_to_xslt(x, changes, "test_19_fix")
    # y = PhysFix.load_srcml_xml("/home/rewong/phys/physfix/test_19_fix_0.xml")
    # PhysFix.apply_xslt(x, y, "test_result")
    # print([q for q in r.findall(".//{http://www.srcML.org/srcML/src}expr")[0]])


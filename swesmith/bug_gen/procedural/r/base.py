from abc import ABC

from swesmith.bug_gen.procedural.base import ProceduralModifier
from tree_sitter import Parser
from tree_sitter_language_pack import get_language

R_LANGUAGE = get_language("r")
ASSIGNMENT_OPERATORS = {"<-", "<<-", ":=", "="}


def parse_r(code: str):
    # central parser helper so every r modifier uses the same grammar setup.
    parser = Parser(R_LANGUAGE)
    return parser.parse(code.encode("utf-8"))


def node_text(source: bytes, node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")


def binary_parts(source: bytes, node):
    # this helper gives one shared interpretation of r binary nodes,
    # which keeps operator handling consistent across all modifiers.
    if node.type != "binary_operator" or len(node.children) < 3:
        return None
    left = node.children[0]
    operator_node = node.children[1]
    right = node.children[2]
    operator = node_text(source, operator_node)
    return left, operator, operator_node, right


def walk(node):
    # simple recursive walk used by all r modifiers.
    yield node
    for child in node.children:
        yield from walk(child)


def is_function_assignment(source: bytes, node) -> bool:
    # protect top-level function wrappers when removing assignments.
    parts = binary_parts(source, node)
    if parts is None:
        return False
    _left, operator, _operator_node, right = parts
    return operator in ASSIGNMENT_OPERATORS and right.type == "function_definition"


class RProceduralModifier(ProceduralModifier, ABC):
    """Base class for R-specific procedural modifications."""

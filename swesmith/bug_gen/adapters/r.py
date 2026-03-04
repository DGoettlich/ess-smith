import warnings

from pathlib import Path
from swesmith.bug_gen.adapters.utils import build_entity
from swesmith.constants import CodeEntity, CodeProperty, TODO_REWRITE
from tree_sitter import Parser
from tree_sitter_language_pack import get_language

R_LANGUAGE = get_language("r")
ASSIGNMENT_OPERATORS = {"<-", "<<-", ":=", "="}


def _node_text(node) -> str:
    # important: use node.text instead of slicing with byte offsets into
    # self.src_code. tree-sitter offsets are file-relative, while src_code here
    # is entity-local. using node.text avoids wrong names/tags for later entities.
    return node.text.decode("utf-8")


def _binary_operator_token(node) -> str | None:
    if node.type != "binary_operator" or len(node.children) < 3:
        return None
    operator_node = node.children[1]
    return _node_text(operator_node).strip()


def _is_assigned_function(node) -> bool:
    # we currently treat assigned function definitions as the r entity unit,
    # for example: foo <- function(...) { ... }.
    if node.type != "binary_operator" or len(node.children) < 3:
        return False
    operator = _binary_operator_token(node)
    if operator not in ASSIGNMENT_OPERATORS:
        return False
    return node.children[2].type == "function_definition"


class REntity(CodeEntity):
    def _analyze_properties(self):
        # r extraction currently models function-level entities only.
        self._tags.add(CodeProperty.IS_FUNCTION)

        stack = [self.node]
        while stack:
            node = stack.pop()
            stack.extend(reversed(node.children))

            if node.type in {"for_statement", "while_statement", "repeat_statement"}:
                self._tags.add(CodeProperty.HAS_LOOP)

            if node.type == "if_statement":
                self._tags.add(CodeProperty.HAS_IF)
                if node.child_by_field_name("alternative") is not None:
                    self._tags.add(CodeProperty.HAS_IF_ELSE)

            if node.type in {"subset"}:
                self._tags.add(CodeProperty.HAS_LIST_INDEXING)

            if node.type == "unary_operator":
                self._tags.add(CodeProperty.HAS_UNARY_OP)

            if node.type == "call":
                self._tags.add(CodeProperty.HAS_FUNCTION_CALL)
                fn_node = node.child_by_field_name("function")
                if fn_node is not None:
                    fn_name = _node_text(fn_node).strip()
                    if fn_name == "return":
                        self._tags.add(CodeProperty.HAS_RETURN)
                    if fn_name in {"library", "require", "source"}:
                        self._tags.add(CodeProperty.HAS_IMPORT)
                    if fn_name in {"tryCatch", "withCallingHandlers", "try"}:
                        self._tags.add(CodeProperty.HAS_EXCEPTION)

            if node.type in {"namespace_operator", "extract_operator"}:
                self._tags.add(CodeProperty.HAS_IMPORT)

            if node.type == "binary_operator":
                op = _binary_operator_token(node)
                if op is None:
                    continue
                # assignment is tracked separately from generic binary ops
                # because remove-assign modifiers depend on this tag.
                if op in ASSIGNMENT_OPERATORS:
                    self._tags.add(CodeProperty.HAS_ASSIGNMENT)
                else:
                    self._tags.add(CodeProperty.HAS_BINARY_OP)
                if op in {"&&", "||", "&", "|"}:
                    self._tags.add(CodeProperty.HAS_BOOL_OP)
                if op in {"<", ">", "<=", ">="}:
                    self._tags.add(CodeProperty.HAS_OFF_BY_ONE)
                if op in {"+", "-", "*", "/", "**", "^"}:
                    self._tags.add(CodeProperty.HAS_ARITHMETIC)

    @property
    def name(self) -> str:
        if self.node.type == "binary_operator" and len(self.node.children) >= 3:
            lhs = _node_text(self.node.children[0]).strip()
            return lhs if lhs else "anonymous_function"
        return "anonymous_function"

    @property
    def signature(self) -> str:
        if self.node.type != "binary_operator" or len(self.node.children) < 3:
            return self.src_code.strip().split("\n", 1)[0]

        function_node = self.node.children[2]
        if function_node.type != "function_definition":
            return self.src_code.strip().split("\n", 1)[0]

        # we derive signature text from the exact node text and split at "{"
        # so this stays stable even when indentation in src_code changes.
        entity_text = _node_text(self.node).strip()
        block_start = entity_text.find("{")
        if block_start < 0:
            return entity_text
        return entity_text[:block_start].rstrip()

    @property
    def stub(self) -> str:
        return f"{self.signature} {{\n  # {TODO_REWRITE}\n}}"

    @property
    def complexity(self) -> int:
        complexity = 1
        stack = [self.node]
        while stack:
            node = stack.pop()
            stack.extend(reversed(node.children))
            if node.type in {
                "if_statement",
                "for_statement",
                "while_statement",
                "repeat_statement",
            }:
                complexity += 1
            elif node.type == "binary_operator":
                op = _binary_operator_token(node)
                # we count assignment and arithmetic here on purpose so
                # simple but mutable functions pass can_change gating.
                if op in ASSIGNMENT_OPERATORS:
                    complexity += 1
                elif op in {"&&", "||", "&", "|"}:
                    complexity += 1
                elif op in {"<", ">", "<=", ">=", "==", "!="}:
                    complexity += 1
                elif op in {"+", "-", "*", "/", "**", "^"}:
                    complexity += 1
        return complexity


def get_entities_from_file_r(
    entities: list[REntity],
    file_path: str | Path,
    max_entities: int = -1,
) -> None:
    parser = Parser(R_LANGUAGE)
    file_path = str(file_path)
    file_content = open(file_path, "r", encoding="utf8").read()
    tree = parser.parse(file_content.encode("utf-8"))
    root = tree.root_node
    lines = file_content.splitlines()

    if root.has_error:
        warnings.warn(f"Error encountered parsing {file_path}", stacklevel=2)

    def walk(node) -> None:
        if 0 <= max_entities == len(entities):
            return

        if node.type == "ERROR":
            warnings.warn(f"Error encountered parsing {file_path}", stacklevel=2)
            return

        if _is_assigned_function(node):
            # we build entities from top-level and nested assigned functions.
            # max_entities is applied during traversal for deterministic cut-off.
            entity = build_entity(
                node, lines, file_path, REntity, default_indent_size=2
            )
            if entity.name:
                entities.append(entity)
            if 0 <= max_entities == len(entities):
                return

        for child in node.children:
            walk(child)

    walk(root)

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.r.base import (
    ASSIGNMENT_OPERATORS,
    binary_parts,
    is_function_assignment,
    parse_r,
    walk,
)
from swesmith.bug_gen.procedural.r.base import RProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity


def _apply_removals(source: bytes, ranges: list[tuple[int, int]]) -> str:
    modified = source
    # remove from right to left so each range still points to the same text.
    for start, end in sorted(ranges, reverse=True):
        modified = modified[:start] + modified[end:]
    return modified.decode("utf-8")


class RemoveLoopModifier(RProceduralModifier):
    explanation: str = CommonPMs.REMOVE_LOOP.explanation
    name: str = CommonPMs.REMOVE_LOOP.name
    conditions: list = CommonPMs.REMOVE_LOOP.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        removals = []

        for node in walk(tree.root_node):
            if node.type in {"for_statement", "while_statement", "repeat_statement"}:
                if self.flip():
                    removals.append((node.start_byte, node.end_byte))

        if not removals:
            return None
        rewrite = _apply_removals(source, removals)
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite, explanation=self.explanation, strategy=self.name
        )


class RemoveConditionalModifier(RProceduralModifier):
    explanation: str = CommonPMs.REMOVE_CONDITIONAL.explanation
    name: str = CommonPMs.REMOVE_CONDITIONAL.name
    conditions: list = CommonPMs.REMOVE_CONDITIONAL.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        removals = []

        for node in walk(tree.root_node):
            if node.type == "if_statement" and self.flip():
                removals.append((node.start_byte, node.end_byte))

        if not removals:
            return None
        rewrite = _apply_removals(source, removals)
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite, explanation=self.explanation, strategy=self.name
        )


class RemoveAssignModifier(RProceduralModifier):
    explanation: str = CommonPMs.REMOVE_ASSIGNMENT.explanation
    name: str = CommonPMs.REMOVE_ASSIGNMENT.name
    conditions: list = CommonPMs.REMOVE_ASSIGNMENT.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        removals = []

        for node in walk(tree.root_node):
            # keep function wrapper assignments (foo <- function(...))
            # so we do not strip the entity boundary itself.
            if is_function_assignment(source, node):
                continue
            parts = binary_parts(source, node)
            if parts is None:
                continue
            _left, operator, _operator_node, _right = parts
            if operator in ASSIGNMENT_OPERATORS and self.flip():
                removals.append((node.start_byte, node.end_byte))

        if not removals:
            return None
        rewrite = _apply_removals(source, removals)
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite, explanation=self.explanation, strategy=self.name
        )

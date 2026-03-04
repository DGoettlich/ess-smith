from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.r.base import (
    ASSIGNMENT_OPERATORS,
    binary_parts,
    node_text,
    parse_r,
    walk,
)
from swesmith.bug_gen.procedural.r.base import RProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity


def _apply_replacements(source: bytes, replacements: list[tuple[int, int, str]]) -> str:
    modified = source
    # apply edits from right to left so byte offsets stay stable.
    for start, end, replacement in sorted(replacements, reverse=True):
        modified = modified[:start] + replacement.encode("utf-8") + modified[end:]
    return modified.decode("utf-8")


class OperationChangeModifier(RProceduralModifier):
    explanation: str = CommonPMs.OPERATION_CHANGE.explanation
    name: str = CommonPMs.OPERATION_CHANGE.name
    conditions: list = CommonPMs.OPERATION_CHANGE.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        replacements = []

        operator_groups = {
            "+": ["+", "-"],
            "-": ["+", "-"],
            "*": ["*", "/", "^", "**"],
            "/": ["*", "/", "^", "**"],
            "^": ["*", "/", "^", "**"],
            "**": ["*", "/", "^", "**"],
            "&&": ["&&", "||"],
            "||": ["&&", "||"],
            "&": ["&", "|"],
            "|": ["&", "|"],
        }

        for node in walk(tree.root_node):
            parts = binary_parts(source, node)
            if parts is None:
                continue
            _left, operator, operator_node, _right = parts
            # skip assignment operators on purpose: changing those tends to
            # destroy basic function structure instead of injecting subtle bugs.
            if operator in ASSIGNMENT_OPERATORS or operator not in operator_groups:
                continue
            if not self.flip():
                continue
            options = [x for x in operator_groups[operator] if x != operator]
            if not options:
                continue
            replacements.append(
                (
                    operator_node.start_byte,
                    operator_node.end_byte,
                    self.rand.choice(options),
                )
            )

        if not replacements:
            return None
        rewrite = _apply_replacements(source, replacements)
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite, explanation=self.explanation, strategy=self.name
        )


class OperationFlipOperatorModifier(RProceduralModifier):
    explanation: str = CommonPMs.OPERATION_FLIP_OPERATOR.explanation
    name: str = CommonPMs.OPERATION_FLIP_OPERATOR.name
    conditions: list = CommonPMs.OPERATION_FLIP_OPERATOR.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        replacements = []

        flipped = {
            "==": "!=",
            "!=": "==",
            "<": ">=",
            ">": "<=",
            "<=": ">",
            ">=": "<",
            "&&": "||",
            "||": "&&",
            "+": "-",
            "-": "+",
        }

        for node in walk(tree.root_node):
            parts = binary_parts(source, node)
            if parts is None:
                continue
            _left, operator, operator_node, _right = parts
            if operator in ASSIGNMENT_OPERATORS or operator not in flipped:
                continue
            if not self.flip():
                continue
            replacements.append(
                (operator_node.start_byte, operator_node.end_byte, flipped[operator])
            )

        if not replacements:
            return None
        rewrite = _apply_replacements(source, replacements)
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite, explanation=self.explanation, strategy=self.name
        )


class OperationSwapOperandsModifier(RProceduralModifier):
    explanation: str = CommonPMs.OPERATION_SWAP_OPERANDS.explanation
    name: str = CommonPMs.OPERATION_SWAP_OPERANDS.name
    conditions: list = CommonPMs.OPERATION_SWAP_OPERANDS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        replacements = []

        flipped_comparison = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}
        for node in walk(tree.root_node):
            parts = binary_parts(source, node)
            if parts is None or not self.flip():
                continue
            left, operator, _operator_node, right = parts
            if operator in ASSIGNMENT_OPERATORS:
                continue
            left_text = node_text(source, left)
            right_text = node_text(source, right)
            # for comparisons we also flip the direction so meaning is
            # preserved except for swapped operand effects.
            op = flipped_comparison.get(operator, operator)
            replacement = f"{right_text} {op} {left_text}"
            replacements.append((node.start_byte, node.end_byte, replacement))

        if not replacements:
            return None
        rewrite = _apply_replacements(source, replacements)
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite, explanation=self.explanation, strategy=self.name
        )


class OperationBreakChainsModifier(RProceduralModifier):
    explanation: str = CommonPMs.OPERATION_BREAK_CHAINS.explanation
    name: str = CommonPMs.OPERATION_BREAK_CHAINS.name
    conditions: list = CommonPMs.OPERATION_BREAK_CHAINS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        replacements = []

        for node in walk(tree.root_node):
            parts = binary_parts(source, node)
            if parts is None:
                continue
            left, operator, _operator_node, right = parts
            if operator in ASSIGNMENT_OPERATORS or not self.flip():
                continue
            if left.type != "binary_operator" and right.type != "binary_operator":
                continue
            chosen = left if self.rand.choice([True, False]) else right
            replacements.append(
                (node.start_byte, node.end_byte, node_text(source, chosen))
            )

        if not replacements:
            return None
        rewrite = _apply_replacements(source, replacements)
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite, explanation=self.explanation, strategy=self.name
        )


class OperationChangeConstantsModifier(RProceduralModifier):
    explanation: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.explanation
    name: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.name
    conditions: list = CommonPMs.OPERATION_CHANGE_CONSTANTS.conditions

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        replacements = []

        for node in walk(tree.root_node):
            if node.type not in {"integer", "float"} or not self.flip():
                continue
            raw = node_text(source, node)
            try:
                if node.type == "integer":
                    value = int(raw)
                    delta = self.rand.choice([-1, 1])
                    replacement = str(value + delta)
                else:
                    value = float(raw)
                    delta = self.rand.choice([-1.0, 1.0])
                    replacement = str(value + delta)
            except ValueError:
                continue
            replacements.append((node.start_byte, node.end_byte, replacement))

        if not replacements:
            return None
        rewrite = _apply_replacements(source, replacements)
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite, explanation=self.explanation, strategy=self.name
        )

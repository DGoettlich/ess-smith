from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.r.base import node_text, parse_r, walk
from swesmith.bug_gen.procedural.r.base import RProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity


class ControlIfElseInvertModifier(RProceduralModifier):
    """Invert if-else statements by swapping consequence and alternative blocks."""

    explanation: str = CommonPMs.CONTROL_IF_ELSE_INVERT.explanation
    name: str = CommonPMs.CONTROL_IF_ELSE_INVERT.name
    conditions: list = CommonPMs.CONTROL_IF_ELSE_INVERT.conditions
    min_complexity: int = 5

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        # parse once, then collect edits, then apply edits from right to left.
        # right-to-left application keeps byte ranges valid after each edit.
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        replacements = []

        for node in walk(tree.root_node):
            if node.type != "if_statement":
                continue
            condition = node.child_by_field_name("condition")
            consequence = node.child_by_field_name("consequence")
            alternative = node.child_by_field_name("alternative")
            if (
                condition is None
                or consequence is None
                or alternative is None
                or not self.flip()
            ):
                continue
            condition_text = node_text(source, condition)
            consequence_text = node_text(source, consequence)
            alternative_text = node_text(source, alternative)
            replacement = (
                f"if ({condition_text}) {alternative_text} else {consequence_text}"
            )
            replacements.append((node.start_byte, node.end_byte, replacement))

        if not replacements:
            return None

        modified = source
        for start, end, replacement in sorted(replacements, reverse=True):
            modified = modified[:start] + replacement.encode("utf-8") + modified[end:]

        rewrite = modified.decode("utf-8")
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite,
            explanation=self.explanation,
            strategy=self.name,
        )


class ControlShuffleLinesModifier(RProceduralModifier):
    """Shuffle top-level statements in function bodies."""

    explanation: str = CommonPMs.CONTROL_SHUFFLE_LINES.explanation
    name: str = CommonPMs.CONTROL_SHUFFLE_LINES.name
    conditions: list = CommonPMs.CONTROL_SHUFFLE_LINES.conditions
    max_complexity: int = 10

    def modify(self, code_entity: CodeEntity) -> BugRewrite | None:
        # we only shuffle named statements inside function bodies.
        # this avoids moving braces/tokens that are not standalone statements.
        tree = parse_r(code_entity.src_code)
        source = code_entity.src_code.encode("utf-8")
        replacements = []

        for node in walk(tree.root_node):
            if node.type != "function_definition":
                continue
            body = node.child_by_field_name("body")
            if body is None or body.type != "braced_expression":
                continue
            statements = [child for child in body.children if child.is_named]
            if len(statements) < 2 or not self.flip():
                continue

            shuffled = statements[:]
            self.rand.shuffle(shuffled)
            # if random shuffle returns original order, skip this attempt.
            if all(a.id == b.id for a, b in zip(statements, shuffled)):
                continue

            indent = " " * (body.start_point[1] + 2)
            body_text = "{\n" + "\n".join(
                f"{indent}{node_text(source, stmt).strip()}" for stmt in shuffled
            )
            body_text += "\n" + (" " * body.start_point[1]) + "}"
            replacements.append((body.start_byte, body.end_byte, body_text))

        if not replacements:
            return None

        modified = source
        # apply from end to start so earlier byte offsets do not drift.
        for start, end, replacement in sorted(replacements, reverse=True):
            modified = modified[:start] + replacement.encode("utf-8") + modified[end:]

        rewrite = modified.decode("utf-8")
        if rewrite == code_entity.src_code:
            return None
        return BugRewrite(
            rewrite=rewrite,
            explanation=self.explanation,
            strategy=self.name,
        )

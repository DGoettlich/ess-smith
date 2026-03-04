from pathlib import Path

from tree_sitter import Parser
from tree_sitter_language_pack import get_language

from swesmith.bug_gen.adapters.r import get_entities_from_file_r
from swesmith.bug_gen.procedural.r.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)

R_LANGUAGE = get_language("r")


def _parseable(src: str) -> bool:
    parser = Parser(R_LANGUAGE)
    return not parser.parse(src.encode("utf-8")).root_node.has_error


def _get_first_entity(tmp_path: Path, src: str):
    test_file = tmp_path / "sample.R"
    test_file.write_text(src, encoding="utf-8")
    entities = []
    get_entities_from_file_r(entities, test_file)
    assert len(entities) == 1
    return entities[0]


def test_control_if_else_invert_modifier(tmp_path):
    src = """foo <- function(x, y) {
  total <- x + y
  if (total > 0 && x < y) {
    total <- total + 1
  } else {
    total <- total - 1
  }
  for (i in 1:3) {
    total <- total + i
  }
  total
}
"""
    entity = _get_first_entity(tmp_path, src)
    modifier = ControlIfElseInvertModifier(likelihood=1.0, seed=42)
    assert modifier.can_change(entity)

    result = modifier.modify(entity)
    assert result is not None
    assert result.rewrite != entity.src_code
    assert "else" in result.rewrite
    assert _parseable(result.rewrite)


def test_control_shuffle_lines_modifier(tmp_path):
    src = """foo <- function(values) {
  total <- 0
  for (v in values) {
    total <- total + v
  }
  result <- total + 1
  result
}
"""
    entity = _get_first_entity(tmp_path, src)
    modifier = ControlShuffleLinesModifier(likelihood=1.0, seed=7)
    assert modifier.can_change(entity)

    rewrite = None
    for _ in range(5):
        result = modifier.modify(entity)
        if result is not None and result.rewrite != entity.src_code:
            rewrite = result.rewrite
            break

    assert rewrite is not None
    assert _parseable(rewrite)

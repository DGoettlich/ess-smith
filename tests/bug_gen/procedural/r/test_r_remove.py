from pathlib import Path

from tree_sitter import Parser
from tree_sitter_language_pack import get_language

from swesmith.bug_gen.adapters.r import get_entities_from_file_r
from swesmith.bug_gen.procedural.r.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
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


def test_remove_loop_modifier(tmp_path):
    src = """foo <- function(values) {
  total <- 0
  for (v in values) {
    total <- total + v
  }
  total
}
"""
    entity = _get_first_entity(tmp_path, src)
    modifier = RemoveLoopModifier(likelihood=1.0, seed=11)
    assert modifier.can_change(entity)
    result = modifier.modify(entity)
    assert result is not None
    assert "for (" not in result.rewrite
    assert _parseable(result.rewrite)


def test_remove_conditional_modifier(tmp_path):
    src = """foo <- function(x) {
  if (x > 0) {
    y <- 1
  } else {
    y <- -1
  }
  y
}
"""
    entity = _get_first_entity(tmp_path, src)
    modifier = RemoveConditionalModifier(likelihood=1.0, seed=12)
    assert modifier.can_change(entity)
    result = modifier.modify(entity)
    assert result is not None
    assert "if (" not in result.rewrite
    assert _parseable(result.rewrite)


def test_remove_assign_modifier_keeps_function_wrapper(tmp_path):
    src = """foo <- function(x) {
  y <- x + 1
  z <- y + 2
  z
}
"""
    entity = _get_first_entity(tmp_path, src)
    modifier = RemoveAssignModifier(likelihood=1.0, seed=13)
    assert modifier.can_change(entity)
    result = modifier.modify(entity)
    assert result is not None
    assert "foo <- function" in result.rewrite
    assert _parseable(result.rewrite)

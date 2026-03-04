from pathlib import Path

from tree_sitter import Parser
from tree_sitter_language_pack import get_language

from swesmith.bug_gen.adapters.r import get_entities_from_file_r
from swesmith.bug_gen.procedural.r.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)

R_LANGUAGE = get_language("r")


def _parseable(src: str) -> bool:
    parser = Parser(R_LANGUAGE)
    return not parser.parse(src.encode("utf-8")).root_node.has_error


def _get_first_entity(tmp_path: Path):
    src = """foo <- function(x, y) {
  total <- x + y
  gate <- total >= 2 && x < y
  score <- (x + y) * (x - y)
  if (gate) {
    score <- score + 1
  }
  return(score)
}
"""
    test_file = tmp_path / "sample.R"
    test_file.write_text(src, encoding="utf-8")
    entities = []
    get_entities_from_file_r(entities, test_file)
    assert len(entities) == 1
    return entities[0]


def test_operation_change_modifier(tmp_path):
    entity = _get_first_entity(tmp_path)
    modifier = OperationChangeModifier(likelihood=1.0, seed=20)
    assert modifier.can_change(entity)
    result = modifier.modify(entity)
    assert result is not None
    assert result.rewrite != entity.src_code
    assert _parseable(result.rewrite)


def test_operation_flip_operator_modifier(tmp_path):
    entity = _get_first_entity(tmp_path)
    modifier = OperationFlipOperatorModifier(likelihood=1.0, seed=21)
    assert modifier.can_change(entity)
    result = modifier.modify(entity)
    assert result is not None
    assert result.rewrite != entity.src_code
    assert _parseable(result.rewrite)


def test_operation_swap_operands_modifier(tmp_path):
    entity = _get_first_entity(tmp_path)
    modifier = OperationSwapOperandsModifier(likelihood=1.0, seed=22)
    assert modifier.can_change(entity)
    result = modifier.modify(entity)
    assert result is not None
    assert result.rewrite != entity.src_code
    assert _parseable(result.rewrite)


def test_operation_break_chains_modifier(tmp_path):
    entity = _get_first_entity(tmp_path)
    modifier = OperationBreakChainsModifier(likelihood=1.0, seed=23)
    assert modifier.can_change(entity)
    result = modifier.modify(entity)
    assert result is not None
    assert result.rewrite != entity.src_code
    assert _parseable(result.rewrite)


def test_operation_change_constants_modifier(tmp_path):
    entity = _get_first_entity(tmp_path)
    modifier = OperationChangeConstantsModifier(likelihood=1.0, seed=24)
    assert modifier.can_change(entity)
    result = modifier.modify(entity)
    assert result is not None
    assert result.rewrite != entity.src_code
    assert _parseable(result.rewrite)

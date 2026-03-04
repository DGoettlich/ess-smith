import re
import warnings

import pytest

from swesmith.bug_gen.adapters.r import get_entities_from_file_r


@pytest.fixture
def r_test_file_entities(test_file_r):
    entities = []
    get_entities_from_file_r(entities, test_file_r)
    assert len(entities) == 3
    return entities


def test_get_entities_from_file_r_max(test_file_r):
    entities = []
    get_entities_from_file_r(entities, test_file_r, 2)
    assert len(entities) == 2
    assert [e.name for e in entities] == ["calculate_score", "aggregate_values"]


def test_get_entities_from_file_r_unreadable():
    with pytest.raises(IOError):
        get_entities_from_file_r([], "non-existent-file")


def test_get_entities_from_file_r_malformed(tmp_path):
    malformed_file = tmp_path / "malformed.R"
    malformed_file.write_text("x <- function( {\n")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_r(entities, malformed_file)
        assert any(
            re.search(r"Error encountered parsing .*malformed.R", str(w.message))
            for w in ws
        )


def test_r_entity_names(r_test_file_entities):
    assert [e.name for e in r_test_file_entities] == [
        "calculate_score",
        "aggregate_values",
        "load_helpers",
    ]


def test_r_entity_signatures(r_test_file_entities):
    signatures = [e.signature for e in r_test_file_entities]
    assert signatures == [
        "calculate_score <- function(x, y)",
        "aggregate_values <- function(values)",
        "load_helpers <- function()",
    ]


def test_r_entity_stub_contains_todo(r_test_file_entities):
    for entity in r_test_file_entities:
        assert "TODO: Implement this function" in entity.stub
        assert entity.stub.startswith(entity.signature)


def test_r_entity_complexity_is_non_trivial(r_test_file_entities):
    complexity_map = {entity.name: entity.complexity for entity in r_test_file_entities}
    assert complexity_map["calculate_score"] > 1
    assert complexity_map["aggregate_values"] > 1
    assert complexity_map["load_helpers"] >= 1

"""Tests for the YAML suite loader."""
import textwrap
from pathlib import Path

import pytest

from rubricon.loader import load_suite
from rubricon.models import Suite

VALID_YAML = textwrap.dedent("""\
    name: test_suite
    description: A test suite
    scenarios:
      - id: s1
        description: desc
        input: "hello"
    rubric:
      criteria:
        - name: correctness
          description: Is it correct?
          weight: 1.0
          descriptors:
            1: "bad"
            5: "great"
          pass_threshold: 3
""")


def test_load_suite_valid(tmp_path: Path):
    p = tmp_path / "suite.yaml"
    p.write_text(VALID_YAML)
    suite = load_suite(p)
    assert isinstance(suite, Suite)
    assert suite.name == "test_suite"
    assert len(suite.scenarios) == 1
    assert suite.scenarios[0].id == "s1"
    assert suite.rubric.criteria[0].name == "correctness"


def test_load_suite_missing_required_field_raises_value_error(tmp_path: Path):
    # Missing 'scenarios'
    bad_yaml = textwrap.dedent("""\
        name: test_suite
        rubric:
          criteria:
            - name: correctness
              description: d
              weight: 1.0
              descriptors:
                1: bad
              pass_threshold: 3
    """)
    p = tmp_path / "bad.yaml"
    p.write_text(bad_yaml)
    with pytest.raises(ValueError, match="Invalid suite YAML"):
        load_suite(p)


def test_load_suite_nonexistent_file_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_suite("/nonexistent/path/suite.yaml")


def test_load_suite_example_yaml():
    import os
    examples = Path(__file__).parent.parent / "examples" / "research_agent_suite.yaml"
    if not examples.exists():
        pytest.skip("Example YAML not found")
    suite = load_suite(examples)
    assert suite.name == "research_agent_suite"
    assert len(suite.scenarios) == 3
    assert len(suite.rubric.criteria) == 2

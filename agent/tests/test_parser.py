from __future__ import annotations

from pathlib import Path

from claude_portal.models import UsageEvent
from claude_portal.parser import (
    decode_project_path,
    discover_jsonl_files,
    parse_all,
    parse_file,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_basic_session_yields_assistant_turns_only():
    events = list(parse_file(FIXTURES / "session_basic.jsonl"))
    assert len(events) == 2
    assert all(isinstance(e, UsageEvent) for e in events)
    assert events[0].model == "claude-opus-4-7"
    assert events[1].model == "claude-sonnet-4-6"


def test_parse_basic_session_token_counts():
    opus, sonnet = list(parse_file(FIXTURES / "session_basic.jsonl"))
    assert opus.input_tokens == 120
    assert opus.output_tokens == 350
    assert opus.cache_creation_tokens == 0
    assert opus.cache_read_tokens == 0
    assert opus.total_tokens == 470
    assert sonnet.input_tokens == 80
    assert sonnet.cache_creation_tokens == 1500
    assert sonnet.cache_read_tokens == 2200
    assert sonnet.total_tokens == 80 + 420 + 1500 + 2200


def test_parse_timestamps_are_timezone_aware():
    events = list(parse_file(FIXTURES / "session_basic.jsonl"))
    for event in events:
        assert event.timestamp.tzinfo is not None


def test_parse_skips_malformed_lines():
    events = list(parse_file(FIXTURES / "session_with_invalid.jsonl"))
    assert len(events) == 2
    assert events[0].input_tokens == 50
    assert events[1].input_tokens == 10
    assert events[1].cache_creation_tokens == 5


def test_decode_project_path_absolute_form():
    encoded = "-Users-himanshu-code-ClaudePortal"
    assert decode_project_path(encoded) == "/Users/himanshu/code/ClaudePortal"


def test_decode_project_path_relative_form():
    assert decode_project_path("some-project") == "some/project"


def test_discover_jsonl_files_returns_empty_for_missing_root(tmp_path: Path):
    assert list(discover_jsonl_files(tmp_path / "does-not-exist")) == []


def test_discover_jsonl_files_walks_subdirectories(tmp_path: Path):
    proj_a = tmp_path / "proj-a"
    proj_a.mkdir()
    (proj_a / "session1.jsonl").write_text("")
    proj_b = tmp_path / "proj-b"
    proj_b.mkdir()
    (proj_b / "session2.jsonl").write_text("")
    (proj_b / "ignore.txt").write_text("noise")

    found = list(discover_jsonl_files(tmp_path))
    assert len(found) == 2
    assert {p.name for p in found} == {"session1.jsonl", "session2.jsonl"}


def test_parse_all_walks_tree_and_decodes_project_path(tmp_path: Path):
    proj_dir = tmp_path / "-tmp-proj"
    proj_dir.mkdir()
    session_file = proj_dir / "abc-uuid.jsonl"
    session_file.write_text(
        '{"type":"assistant","timestamp":"2026-05-14T12:00:00Z",'
        '"message":{"model":"claude-opus-4-7","usage":{"input_tokens":1,"output_tokens":2}}}\n'
    )

    events = list(parse_all(tmp_path))
    assert len(events) == 1
    assert events[0].session_id == "abc-uuid"
    assert events[0].project_path == "/tmp/proj"
    assert events[0].total_tokens == 3


def test_parse_deduplicates_same_message_id(tmp_path: Path):
    # Claude Code writes the same API response 2-5× to the JSONL with the same message.id.
    # Only the first occurrence should be counted.
    proj_dir = tmp_path / "-tmp-proj"
    proj_dir.mkdir()
    session_file = proj_dir / "abc-uuid.jsonl"
    line = (
        '{"type":"assistant","timestamp":"2026-05-14T12:00:00Z",'
        '"message":{"id":"msg_abc","model":"claude-sonnet-4-6",'
        '"usage":{"input_tokens":100,"output_tokens":200,"cache_creation_input_tokens":50}}}\n'
    )
    session_file.write_text(line * 4)  # same message written 4 times

    events = list(parse_file(session_file))
    assert len(events) == 1
    assert events[0].input_tokens == 100
    assert events[0].output_tokens == 200
    assert events[0].cache_creation_tokens == 50


def test_parse_counts_distinct_message_ids_separately(tmp_path: Path):
    proj_dir = tmp_path / "-tmp-proj"
    proj_dir.mkdir()
    session_file = proj_dir / "abc-uuid.jsonl"
    line_a = (
        '{"type":"assistant","timestamp":"2026-05-14T12:00:00Z",'
        '"message":{"id":"msg_aaa","model":"claude-sonnet-4-6",'
        '"usage":{"input_tokens":100,"output_tokens":0,"cache_creation_input_tokens":0}}}\n'
    )
    line_b = (
        '{"type":"assistant","timestamp":"2026-05-14T12:01:00Z",'
        '"message":{"id":"msg_bbb","model":"claude-sonnet-4-6",'
        '"usage":{"input_tokens":200,"output_tokens":0,"cache_creation_input_tokens":0}}}\n'
    )
    # msg_aaa appears 3 times, msg_bbb appears 2 times — only 2 unique events
    session_file.write_text(line_a * 3 + line_b * 2)

    events = list(parse_file(session_file))
    assert len(events) == 2
    assert sum(e.input_tokens for e in events) == 300  # 100 + 200, not 700

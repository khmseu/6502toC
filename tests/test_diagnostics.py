"""Tests for Phase 5: diagnostics warning heuristics and end-to-end conversion."""

from pathlib import Path

import pytest

from listing_to_cpp.converter import convert_listing_to_cpp
from listing_to_cpp.diagnostics import run_diagnostics
from listing_to_cpp.ir import build_ir
from listing_to_cpp.parser import parse_listing

EXAMPLE_LISTING = Path(__file__).resolve().parents[1] / "example" / "EI.LST"


# ---------------------------------------------------------------------------
# Heuristic 1: data directive appearing within an executable address region
# ---------------------------------------------------------------------------


def test_data_directive_inside_instruction_range_emits_warning():
    listing_text = (
        "1000  A9 01             LDA   #$01\n"
        "1002  85 02             STA   $02\n"
        "1004              DB    $01,$02\n"
        "1006  60                RTS\n"
    )
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    warnings = run_diagnostics(parsed, ir)

    kinds = [w["kind"] for w in warnings]
    assert "data_in_executable_region" in kinds

    data_warn = next(w for w in warnings if w["kind"] == "data_in_executable_region")
    assert data_warn["address"] == "1004"
    assert data_warn["directive"] == "DB"
    assert "1004" in data_warn["message"]


def test_data_directive_outside_instruction_range_no_warning():
    listing_text = (
        "1000  A9 01             LDA   #$01\n"
        "1002  60                RTS\n"
        "2000              DB    $01,$02\n"
    )
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    warnings = run_diagnostics(parsed, ir)

    kinds = [w["kind"] for w in warnings]
    assert "data_in_executable_region" not in kinds


def test_no_instructions_means_no_data_in_code_warning():
    listing_text = "1000              DB    $01,$02\n"
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    warnings = run_diagnostics(parsed, ir)

    kinds = [w["kind"] for w in warnings]
    assert "data_in_executable_region" not in kinds


# ---------------------------------------------------------------------------
# Heuristic 2: branch/jump target overlaps with known data region
# ---------------------------------------------------------------------------


def test_jump_to_data_region_emits_warning():
    listing_text = (
        "1000  A9 01             LDA   #$01\n"
        "1002  4C 00 20          JMP   $2000\n"
        "2000              DB    $01,$02\n"
    )
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    warnings = run_diagnostics(parsed, ir)

    kinds = [w["kind"] for w in warnings]
    assert "jump_to_data_region" in kinds

    jmp_warn = next(w for w in warnings if w["kind"] == "jump_to_data_region")
    assert jmp_warn["mnemonic"] == "JMP"
    assert jmp_warn["target_address"] == 0x2000
    assert "$2000" in jmp_warn["message"]


def test_branch_to_data_region_emits_warning():
    listing_text = (
        "1000  A9 01             LDA   #$01\n"
        "1002  F0 04             BEQ   $1008\n"
        "1004  60                RTS\n"
        "1008              DB    $01,$02\n"
    )
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    warnings = run_diagnostics(parsed, ir)

    kinds = [w["kind"] for w in warnings]
    assert "jump_to_data_region" in kinds

    w = next(w for w in warnings if w["kind"] == "jump_to_data_region")
    assert w["mnemonic"] == "BEQ"
    assert w["target_address"] == 0x1008


def test_jsr_to_data_region_emits_warning():
    listing_text = (
        "1000  20 00 20          JSR   $2000\n"
        "1003  60                RTS\n"
        "2000              DB    $48,$65,$6C\n"
    )
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    warnings = run_diagnostics(parsed, ir)

    kinds = [w["kind"] for w in warnings]
    assert "jump_to_data_region" in kinds


def test_jump_to_instruction_region_no_warning():
    listing_text = (
        "1000  A9 01             LDA   #$01\n"
        "1002  4C 06 10          JMP   $1006\n"
        "1005  60                RTS\n"
        "1006  A9 02             LDA   #$02\n"
        "1008  60                RTS\n"
    )
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    warnings = run_diagnostics(parsed, ir)

    kinds = [w["kind"] for w in warnings]
    assert "jump_to_data_region" not in kinds


def test_symbolic_jump_to_data_region_emits_warning():
    listing_text = (
        "TABLE EQU $2000\n"
        "1000  20 00 20          JSR   TABLE\n"
        "2000              DB    $01,$02\n"
    )
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    warnings = run_diagnostics(parsed, ir)

    kinds = [w["kind"] for w in warnings]
    assert "jump_to_data_region" in kinds

    w = next(w for w in warnings if w["kind"] == "jump_to_data_region")
    assert w["target_address"] == 0x2000


# ---------------------------------------------------------------------------
# Integration: converter returns diagnostics
# ---------------------------------------------------------------------------


def test_converter_returns_diagnostics_dict(tmp_path: Path):
    input_path = tmp_path / "input.lst"
    output_path = tmp_path / "out.cpp"
    input_path.write_text(
        "1000  A9 01             LDA   #$01\n"
        "1002  4C 00 20          JMP   $2000\n"
        "2000              DB    $01,$02\n",
        encoding="ascii",
    )

    result = convert_listing_to_cpp(input_path, output_path)

    assert result is not None
    assert "warnings" in result
    kinds = [w["kind"] for w in result["warnings"]]
    assert "jump_to_data_region" in kinds


def test_converter_returns_dict_with_warnings_key_even_for_clean_listing(
    tmp_path: Path,
):
    input_path = tmp_path / "input.lst"
    output_path = tmp_path / "out.cpp"
    input_path.write_text("SAMPLE LISTING\n", encoding="ascii")

    result = convert_listing_to_cpp(input_path, output_path)

    assert isinstance(result, dict)
    assert "warnings" in result
    assert isinstance(result["warnings"], list)


# ---------------------------------------------------------------------------
# End-to-end: EI.LST sample listing
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not EXAMPLE_LISTING.exists(), reason="EI.LST not found")
def test_end_to_end_ei_listing_converts_without_exception(tmp_path: Path):
    output_path = tmp_path / "EI.cpp"

    # Must not raise
    result = convert_listing_to_cpp(EXAMPLE_LISTING, output_path)

    assert output_path.exists(), "Output file was not created"
    content = output_path.read_text(encoding="ascii")
    assert len(content) > 0, "Output file is empty"
    assert "namespace converted" in content, "Expected C++ namespace scaffold"
    assert isinstance(result, dict)
    assert "warnings" in result


@pytest.mark.skipif(not EXAMPLE_LISTING.exists(), reason="EI.LST not found")
def test_end_to_end_ei_listing_output_is_ascii(tmp_path: Path):
    output_path = tmp_path / "EI.cpp"
    convert_listing_to_cpp(EXAMPLE_LISTING, output_path)
    # If not pure ASCII, read_text with ascii encoding would raise UnicodeDecodeError
    content = output_path.read_text(encoding="ascii")
    assert len(content) > 0

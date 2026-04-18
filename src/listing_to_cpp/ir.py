"""IR builder for symbol and operand resolution."""

from __future__ import annotations

import re

_DIRECT_HEX_RE = re.compile(r"^\$([0-9A-Fa-f]{1,6})$")
_DIRECT_DEC_RE = re.compile(r"^[0-9]+$")
_SYMBOL_RE = re.compile(r"^[A-Za-z_][\w.]*$")
_INDEXED_OPERAND_RE = re.compile(r"^(?P<base>[^,]+?)\s*,\s*(?P<index>[XxYy])$")


def _parse_numeric(value: str):
    raw = value.strip()
    hex_match = _DIRECT_HEX_RE.match(raw)
    if hex_match:
        return int(hex_match.group(1), 16)

    if raw.lower().startswith("0x"):
        try:
            return int(raw, 16)
        except ValueError:
            return None

    if _DIRECT_DEC_RE.match(raw):
        return int(raw, 10)

    return None


def _split_indexed_operand(operand: str):
    match = _INDEXED_OPERAND_RE.match(operand.strip())
    if match is None:
        return operand.strip(), None
    return match.group("base").strip(), match.group("index").upper()


def _resolve_operand_address(
    operand: str | None,
    symbols: dict[str, dict],
    symbol_lookup: dict[str, dict],
):
    if operand is None:
        return None, None

    normalized = operand.strip()
    if not normalized:
        return None, None

    if normalized.startswith("#"):
        return None, None

    base_operand, _ = _split_indexed_operand(normalized)

    direct = _parse_numeric(base_operand)
    if direct is not None:
        return direct, "direct"

    if _SYMBOL_RE.match(base_operand):
        symbol = symbol_lookup.get(base_operand.lower())
        if symbol is None:
            symbol = symbols.get(base_operand)
        if symbol is not None and symbol.get("value") is not None:
            return symbol["value"], "symbolic"

    return None, None


def build_ir(parsed_listing):
    """Build Phase 3 IR with symbols, instructions, I/O accesses, and warnings."""
    records = parsed_listing.get("records", [])

    symbols: dict[str, dict] = {}
    symbol_lookup: dict[str, dict] = {}
    for record in records:
        if record.get("type") != "equ":
            continue

        raw_value = record.get("value", "")
        is_alias = bool(record.get("is_current_location_alias", False))
        symbols[record["name"]] = {
            "raw_value": raw_value,
            "value": None if is_alias else _parse_numeric(raw_value),
            "is_current_location_alias": is_alias,
            "line": record.get("line"),
        }
        symbol_lookup[record["name"].lower()] = symbols[record["name"]]

    instructions = []
    io_accesses = []
    warnings = []

    for record in records:
        if record.get("type") != "instruction":
            continue

        instruction = {
            "line": record.get("line"),
            "address": _parse_numeric(record.get("address", "")),
            "mnemonic": record.get("mnemonic"),
            "operand": record.get("operand"),
            "label": record.get("label"),
            "bytes": list(record.get("bytes", [])),
        }
        instructions.append(instruction)

        operand = record.get("operand")
        resolved_address, source = _resolve_operand_address(
            operand, symbols, symbol_lookup
        )

        if resolved_address is not None and 0xC000 <= resolved_address <= 0xCFFF:
            io_accesses.append(
                {
                    "line": record.get("line"),
                    "mnemonic": record.get("mnemonic"),
                    "operand": operand,
                    "source": source,
                    "resolved_address": resolved_address,
                    "classification": "explicit_c000_cfff",
                }
            )

        if operand and "(" in operand and ")" in operand and resolved_address is None:
            warnings.append(
                {
                    "kind": "uncertain_indirect_access",
                    "line": record.get("line"),
                    "mnemonic": record.get("mnemonic"),
                    "operand": operand,
                    "message": "Unresolved indirect memory access; cannot determine whether it targets 0xC000-0xCFFF.",
                }
            )

    return {
        "symbols": symbols,
        "instructions": instructions,
        "io_accesses": io_accesses,
        "warnings": warnings,
    }

"""Listing parser with tolerant line classification."""

from __future__ import annotations

import re

_DATA_DIRECTIVES = {"DB", "DW", "DS", "ASC", "STR"}
_HEADER_RE = re.compile(r"^-{3,}.*-{3,}$")
_MARKER_RE = re.compile(r"^(SOURCE|INCLUDE)\b\s*(.*)$", re.IGNORECASE)
_EQU_RE = re.compile(
    r"^(?P<name>[A-Za-z_][\w.]*)\s+EQU\s+(?P<value>\*|[^;]+?)\s*$",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(r"^[0-9A-Fa-f]{4,6}$")
_BYTE_RE = re.compile(r"^[0-9A-Fa-f]{2}$")
_KNOWN_MNEMONICS = {
    "ADC",
    "AND",
    "ASL",
    "BCC",
    "BCS",
    "BEQ",
    "BIT",
    "BMI",
    "BNE",
    "BPL",
    "BRA",
    "BRK",
    "BVC",
    "BVS",
    "CLC",
    "CLD",
    "CLI",
    "CLV",
    "CMP",
    "CPX",
    "CPY",
    "DEC",
    "DEX",
    "DEY",
    "EOR",
    "INC",
    "INX",
    "INY",
    "JMP",
    "JSR",
    "LDA",
    "LDX",
    "LDY",
    "LSR",
    "NOP",
    "ORA",
    "PHA",
    "PHP",
    "PHX",
    "PHY",
    "PLA",
    "PLP",
    "PLX",
    "PLY",
    "ROL",
    "ROR",
    "RTI",
    "RTS",
    "SBC",
    "SEC",
    "SED",
    "SEI",
    "STA",
    "STP",
    "STX",
    "STY",
    "STZ",
    "TAX",
    "TAY",
    "TRB",
    "TSB",
    "TSX",
    "TXA",
    "TXS",
    "TYA",
    "WAI",
}


def _is_mnemonic(token: str) -> bool:
    upper_token = token.upper()
    return len(upper_token) == 3 and upper_token in _KNOWN_MNEMONICS


def _parse_code_record(raw_line: str, line_number: int):
    code_part, has_comment, comment_part = raw_line.partition(";")
    comment = comment_part.strip() if has_comment else None
    tokens = code_part.strip().split()
    if not tokens:
        return None

    token_index = 0
    address = None
    data_bytes: list[str] = []

    if _ADDRESS_RE.match(tokens[token_index]):
        address = tokens[token_index].upper()
        token_index += 1
        while token_index < len(tokens) and _BYTE_RE.match(tokens[token_index]):
            data_bytes.append(tokens[token_index].upper())
            token_index += 1

    # EI listing instruction/data lines generally carry an address field.
    if address is None:
        return None

    remaining = tokens[token_index:]
    if not remaining:
        return None

    directive_index = None
    directive = None
    for idx, token in enumerate(remaining[:2]):
        upper_token = token.upper()
        if upper_token in _DATA_DIRECTIVES:
            directive_index = idx
            directive = upper_token
            break

    if directive is not None and directive_index is not None:
        label = remaining[0] if directive_index == 1 else None
        operand_tokens = remaining[directive_index + 1 :]
        return {
            "type": "data_directive",
            "address": address,
            "label": label,
            "directive": directive,
            "operand": " ".join(operand_tokens).strip(),
            "line": line_number,
            "raw": raw_line,
        }

    label = None
    mnemonic = None
    operand_tokens: list[str] = []
    if _is_mnemonic(remaining[0]):
        mnemonic = remaining[0].upper()
        operand_tokens = remaining[1:]
    elif len(remaining) >= 2 and _is_mnemonic(remaining[1]):
        label = remaining[0]
        mnemonic = remaining[1].upper()
        operand_tokens = remaining[2:]

    if mnemonic is None:
        return None

    return {
        "type": "instruction",
        "address": address,
        "bytes": data_bytes,
        "label": label,
        "mnemonic": mnemonic,
        "operand": " ".join(operand_tokens).strip() or None,
        "comment": comment,
        "line": line_number,
        "raw": raw_line,
    }


def parse_listing(text: str):
    """Parse listing lines into tolerant typed records."""
    records = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.startswith(";"):
            records.append(
                {
                    "type": "comment",
                    "comment": stripped[1:].strip(),
                    "line": line_number,
                    "raw": raw_line,
                }
            )
            continue

        marker_match = _MARKER_RE.match(stripped)
        if marker_match:
            keyword = marker_match.group(1).upper()
            value = marker_match.group(2).strip()
            marker_type = "source_marker" if keyword == "SOURCE" else "include_marker"
            records.append(
                {
                    "type": marker_type,
                    "keyword": keyword,
                    "value": value,
                    "line": line_number,
                    "raw": raw_line,
                }
            )
            continue

        if _HEADER_RE.match(stripped):
            records.append(
                {
                    "type": "header_marker",
                    "value": stripped,
                    "line": line_number,
                    "raw": raw_line,
                }
            )
            continue

        equ_candidate = stripped.split(";", 1)[0].rstrip()
        equ_match = _EQU_RE.match(equ_candidate)
        if equ_match:
            value = equ_match.group("value").strip()
            records.append(
                {
                    "type": "equ",
                    "name": equ_match.group("name"),
                    "value": value,
                    "is_current_location_alias": value == "*",
                    "line": line_number,
                    "raw": raw_line,
                }
            )
            continue

        code_record = _parse_code_record(raw_line=raw_line, line_number=line_number)
        if code_record is not None:
            records.append(code_record)
            continue

        records.append(
            {
                "type": "unknown",
                "line": line_number,
                "raw": raw_line,
            }
        )

    return {
        "raw": text,
        "records": records,
    }

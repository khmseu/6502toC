"""Diagnostics: warning heuristics for code-as-data ambiguity."""

from __future__ import annotations

_BRANCH_MNEMONICS = frozenset(
    {"BCC", "BCS", "BEQ", "BMI", "BNE", "BPL", "BRA", "BVC", "BVS"}
)
_JUMP_MNEMONICS = frozenset({"JMP", "JSR"})
_BRANCH_JUMP_MNEMONICS = _BRANCH_MNEMONICS | _JUMP_MNEMONICS


def _parse_hex_address(addr: str | None) -> int | None:
    if addr is None:
        return None
    try:
        return int(addr.strip(), 16)
    except (ValueError, AttributeError):
        return None


def _parse_numeric_token(token: str | None) -> int | None:
    if token is None:
        return None
    s = token.strip()
    if not s:
        return None
    if s.startswith("$"):
        try:
            return int(s[1:], 16)
        except ValueError:
            return None
    if s.lower().startswith("0x"):
        try:
            return int(s, 16)
        except ValueError:
            return None
    try:
        return int(s, 10)
    except ValueError:
        return None


def _string_literal_length(operand: str) -> int | None:
    s = operand.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {"'", '"'}:
        return len(s[1:-1])
    return None


def _count_csv_values(operand: str) -> int | None:
    parts = [part.strip() for part in operand.split(",") if part.strip()]
    if not parts:
        return None
    return len(parts)


def _data_size_bytes(record: dict) -> int:
    directive = (record.get("directive") or "").upper()
    operand = (record.get("operand") or "").strip()

    if directive == "DB":
        value_count = _count_csv_values(operand)
        return value_count if value_count is not None else 1

    if directive == "DW":
        value_count = _count_csv_values(operand)
        if value_count is None:
            return 1
        return max(1, 2 * value_count)

    if directive == "DS":
        count = _parse_numeric_token(operand)
        if count is None:
            return 1
        return max(1, count)

    if directive in {"ASC", "STR"}:
        text_length = _string_literal_length(operand)
        if text_length is None:
            return 1
        return max(1, text_length)

    return 1


def _data_interval(record: dict) -> tuple[int, int] | None:
    start = _parse_hex_address(record.get("address"))
    if start is None:
        return None
    size = _data_size_bytes(record)
    end = start + size - 1
    return start, end


def _resolve_target(operand: str, symbol_lookup: dict) -> int | None:
    """Try to resolve a branch/jump operand to a numeric address."""
    s = operand.strip()
    if not s:
        return None
    # Strip index register suffix (e.g. "$2000,X")
    if "," in s:
        s = s.split(",")[0].strip()
    # Remove indirect parens
    s = s.strip("()")
    if s.startswith("$"):
        try:
            return int(s[1:], 16)
        except ValueError:
            return None
    if s.lower().startswith("0x"):
        try:
            return int(s, 16)
        except ValueError:
            return None
    try:
        return int(s)
    except ValueError:
        pass
    sym = symbol_lookup.get(s.lower())
    if sym is not None and sym.get("value") is not None:
        return sym["value"]
    return None


def run_diagnostics(parsed_listing: dict, ir: dict) -> list[dict]:
    """Analyse parsed_listing and ir, return a list of diagnostic warning dicts.

    Heuristics:
    1. Data directive appearing within an executable address region
       (address falls between min and max instruction address).
    2. Branch/jump target that overlaps with a known data directive address.
    """
    records = parsed_listing.get("records", [])
    warnings: list[dict] = []

    # Collect instruction addresses
    instruction_addrs: set[int] = set()
    for r in records:
        if r.get("type") == "instruction":
            addr = _parse_hex_address(r.get("address"))
            if addr is not None:
                instruction_addrs.add(addr)

    # Collect data directive intervals
    data_intervals: list[tuple[int, int, dict]] = []
    for r in records:
        if r.get("type") == "data_directive":
            interval = _data_interval(r)
            if interval is not None:
                data_intervals.append((interval[0], interval[1], r))

    # Heuristic 1: data directive address inside instruction address range
    if instruction_addrs:
        min_instr = min(instruction_addrs)
        max_instr = max(instruction_addrs)
        for data_start, data_end, r in data_intervals:
            if data_start <= max_instr and data_end >= min_instr:
                warnings.append(
                    {
                        "kind": "data_in_executable_region",
                        "line": r.get("line"),
                        "address": r.get("address"),
                        "interval_start": data_start,
                        "interval_end": data_end,
                        "directive": r.get("directive"),
                        "message": (
                            f"Data directive {r.get('directive')} at "
                            f"${data_start:04X}-${data_end:04X} appears within executable "
                            f"address region ${min_instr:04X}-${max_instr:04X}."
                        ),
                    }
                )

    # Heuristic 2: branch/jump target overlaps with known data region
    if data_intervals:
        symbols = ir.get("symbols", {})
        symbol_lookup = {k.lower(): v for k, v in symbols.items()}

        for r in records:
            if r.get("type") != "instruction":
                continue
            mnemonic = (r.get("mnemonic") or "").upper()
            if mnemonic not in _BRANCH_JUMP_MNEMONICS:
                continue
            operand = r.get("operand") or ""
            target = _resolve_target(operand, symbol_lookup)
            if target is None:
                continue
            for data_start, data_end, _ in data_intervals:
                if data_start <= target <= data_end:
                    warnings.append(
                        {
                            "kind": "jump_to_data_region",
                            "line": r.get("line"),
                            "address": r.get("address"),
                            "mnemonic": mnemonic,
                            "operand": operand,
                            "target_address": target,
                            "data_interval_start": data_start,
                            "data_interval_end": data_end,
                            "message": (
                                f"{mnemonic} at ${r.get('address')} targets "
                                f"${target:04X} which overlaps data interval "
                                f"${data_start:04X}-${data_end:04X}."
                            ),
                        }
                    )
                    break

    return warnings

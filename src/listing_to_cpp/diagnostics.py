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

    # Collect data directive addresses
    data_addrs: set[int] = set()
    for r in records:
        if r.get("type") == "data_directive":
            addr = _parse_hex_address(r.get("address"))
            if addr is not None:
                data_addrs.add(addr)

    # Heuristic 1: data directive address inside instruction address range
    if instruction_addrs:
        min_instr = min(instruction_addrs)
        max_instr = max(instruction_addrs)
        for r in records:
            if r.get("type") != "data_directive":
                continue
            addr = _parse_hex_address(r.get("address"))
            if addr is not None and min_instr <= addr <= max_instr:
                warnings.append(
                    {
                        "kind": "data_in_executable_region",
                        "line": r.get("line"),
                        "address": r.get("address"),
                        "directive": r.get("directive"),
                        "message": (
                            f"Data directive {r.get('directive')} at "
                            f"${r.get('address')} appears within executable "
                            f"address region ${min_instr:04X}-${max_instr:04X}."
                        ),
                    }
                )

    # Heuristic 2: branch/jump target overlaps with known data region
    if data_addrs:
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
            if target is not None and target in data_addrs:
                warnings.append(
                    {
                        "kind": "jump_to_data_region",
                        "line": r.get("line"),
                        "address": r.get("address"),
                        "mnemonic": mnemonic,
                        "operand": operand,
                        "target_address": target,
                        "message": (
                            f"{mnemonic} at ${r.get('address')} targets "
                            f"${target:04X} which is a known data directive address."
                        ),
                    }
                )

    return warnings

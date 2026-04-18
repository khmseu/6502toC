"""Code generator: emit legal C++ from 6502 IR."""

from __future__ import annotations

import re

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_]")

# Mnemonics that read memory into a register
_LOAD_MNEMONICS = frozenset(
    {
        "LDA",
        "LDX",
        "LDY",
        "CMP",
        "CPX",
        "CPY",
        "ADC",
        "SBC",
        "AND",
        "ORA",
        "EOR",
        "BIT",
    }
)

# Mnemonics that write a register to memory
_STORE_MNEMONICS = frozenset({"STA", "STX", "STY", "STZ"})

_MNEMONIC_DEST_REG: dict[str, str] = {
    "LDA": "ctx.A",
    "LDX": "ctx.X",
    "LDY": "ctx.Y",
    "CMP": "ctx.A",
    "CPX": "ctx.X",
    "CPY": "ctx.Y",
    "ADC": "ctx.A",
    "SBC": "ctx.A",
    "AND": "ctx.A",
    "ORA": "ctx.A",
    "EOR": "ctx.A",
}

_MNEMONIC_SRC_REG: dict[str, str] = {
    "STA": "ctx.A",
    "STX": "ctx.X",
    "STY": "ctx.Y",
    "STZ": "0U",
}


def _sanitize(name: str) -> str:
    """Convert assembler symbol to a valid C++ identifier."""
    result = _SANITIZE_RE.sub("_", name)
    if result and result[0].isdigit():
        result = "_" + result
    return result


def _parse_numeric(raw: str) -> int | None:
    s = raw.strip()
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
        return None


def _find_sym_cpp(name: str, resolved_syms: dict) -> str | None:
    """Return sanitized C++ name for a symbol, case-insensitive. None if not found."""
    stripped = name.strip()
    if stripped in resolved_syms:
        return _sanitize(stripped)
    for k in resolved_syms:
        if k.lower() == stripped.lower():
            return _sanitize(k)
    return None


def _emit_immediate_expr(operand: str, resolved_syms: dict) -> str | None:
    """Return a legal C++ expression for an immediate operand (#...).

    Returns None when the operand is not an immediate or not recognizable.
    """
    if not operand.startswith("#"):
        return None
    raw = operand[1:].strip()

    if raw.startswith("<"):
        inner = raw[1:].strip()
        sym = _find_sym_cpp(inner, resolved_syms)
        if sym:
            return f"static_cast<std::uint8_t>({sym} & 0xFFU)"
        val = _parse_numeric(inner)
        if val is not None:
            return f"0x{val & 0xFF:02X}U"
        return f"static_cast<std::uint8_t>({_sanitize(inner)} & 0xFFU)"

    if raw.startswith(">"):
        inner = raw[1:].strip()
        sym = _find_sym_cpp(inner, resolved_syms)
        if sym:
            return f"static_cast<std::uint8_t>(({sym} >> 8) & 0xFFU)"
        val = _parse_numeric(inner)
        if val is not None:
            return f"0x{(val >> 8) & 0xFF:02X}U"
        return f"static_cast<std::uint8_t>(({_sanitize(inner)} >> 8) & 0xFFU)"

    return None


_INDEXED_SUFFIX_RE = re.compile(r",\s*([XxYy])\s*$")


def _index_register_from_operand(operand: str) -> str | None:
    """Return 'ctx.X' or 'ctx.Y' if operand has an index suffix, else None."""
    m = _INDEXED_SUFFIX_RE.search(operand)
    if m is None:
        return None
    return f"ctx.{m.group(1).upper()}"


def _emit_instruction_lines(
    instr: dict,
    io_lookup: dict,
    resolved_syms: dict,
) -> list[str]:
    """Return one or more source lines for a single instruction record."""
    mnemonic: str = instr.get("mnemonic") or ""
    operand: str = instr.get("operand") or ""
    line_num: int = instr.get("line") or 0
    label: str | None = instr.get("label")

    cmt = f"/* {mnemonic}{(' ' + operand) if operand else ''} */"
    lines: list[str] = []

    if label:
        lines.append(f"_lbl_{_sanitize(label)}:")

    # ---- I/O shim path for classified C000-CFFF accesses ------------------
    io_access = io_lookup.get((line_num, mnemonic))
    if io_access:
        base_expr = f"0x{io_access['resolved_address']:04X}U"
        idx_reg = _index_register_from_operand(io_access.get("operand") or "")
        addr_expr = f"{base_expr} + {idx_reg}" if idx_reg else base_expr
        if mnemonic in _STORE_MNEMONICS:
            src = _MNEMONIC_SRC_REG.get(mnemonic, "0U")
            lines.append(f"    io_write({addr_expr}, {src}); {cmt}")
        elif mnemonic in _LOAD_MNEMONICS:
            dest = _MNEMONIC_DEST_REG.get(mnemonic)
            if dest:
                lines.append(f"    {dest} = io_read({addr_expr}); {cmt}")
            else:
                lines.append(f"    (void)io_read({addr_expr}); {cmt}")
        else:
            lines.append(f"    (void)io_read({addr_expr}); {cmt}")
        return lines

    # ---- Immediate byte-wise path (#<SYM / #>SYM) --------------------------
    if operand.startswith("#"):
        expr = _emit_immediate_expr(operand, resolved_syms)
        if expr is not None:
            dest = _MNEMONIC_DEST_REG.get(mnemonic)
            if dest:
                lines.append(f"    {dest} = {expr}; {cmt}")
                return lines

    # ---- Default stub: warn at runtime ----------------------------------
    asm_text = f"{mnemonic}{(' ' + operand) if operand else ''}"
    lines.append(f'    std::fprintf(stderr, "unimplemented: {asm_text}\\n"); {cmt}')
    return lines


def generate_cpp(ir: dict, source_line_count: int) -> str:
    """Generate deterministic legal C++ from the Phase 3 IR."""
    symbols: dict = ir.get("symbols", {})
    instructions: list = ir.get("instructions", [])
    io_accesses: list = ir.get("io_accesses", [])

    io_lookup: dict = {(acc["line"], acc["mnemonic"]): acc for acc in io_accesses}

    resolved_syms: dict = {
        name: info
        for name, info in symbols.items()
        if not info.get("is_current_location_alias") and info.get("value") is not None
    }

    # Collect entry labels in order of first appearance
    entry_labels: list[str] = []
    seen_labels: set[str] = set()
    for instr in instructions:
        lbl: str | None = instr.get("label")
        if lbl and lbl not in seen_labels:
            entry_labels.append(lbl)
            seen_labels.add(lbl)

    has_entries = bool(entry_labels)

    out: list[str] = []

    # ---- File header -------------------------------------------------------
    out.append("// Auto-generated by listing_to_cpp")
    out.append("#include <cstdint>")
    out.append("#include <cstdio>")
    out.append("")
    out.append("namespace converted {")
    out.append("")

    # ---- I/O shim interface ------------------------------------------------
    out.append("// I/O shim interface (implementation provided by caller)")
    out.append("extern std::uint8_t io_read(std::uint16_t addr);")
    out.append("extern void io_write(std::uint16_t addr, std::uint8_t val);")
    out.append("")

    # ---- Context struct ----------------------------------------------------
    out.append("// 6502 machine context")
    out.append("struct Context {")
    out.append("    std::uint8_t A{0};")
    out.append("    std::uint8_t X{0};")
    out.append("    std::uint8_t Y{0};")
    out.append("    std::uint8_t SP{0xFFU};")
    out.append("    std::uint8_t P{0};")
    out.append("};")
    out.append("")

    # ---- Symbol constants --------------------------------------------------
    if resolved_syms:
        out.append("// Symbol constants")
        for name, info in resolved_syms.items():
            value: int = info["value"]
            cpp_name = _sanitize(name)
            if value > 0xFF:
                type_str = "std::uint16_t"
                val_str = f"0x{value:04X}U"
            else:
                type_str = "std::uint8_t"
                val_str = f"0x{value:02X}U"
            out.append(f"constexpr {type_str} {cpp_name} = {val_str};")
        out.append("")

    # ---- Entry point enum --------------------------------------------------
    if has_entries:
        out.append("// Entry points")
        out.append("enum class EntryPoint : int {")
        for idx, lbl in enumerate(entry_labels):
            out.append(f"    ENTRY_{_sanitize(lbl)} = {idx},")
        out.append("};")
        out.append("")

    # ---- Forward declarations ----------------------------------------------
    if has_entries:
        first_cpp = _sanitize(entry_labels[0])
        out.append(
            f"void run(Context& ctx, EntryPoint entry = EntryPoint::ENTRY_{first_cpp});"
        )
        for lbl in entry_labels:
            out.append(f"void run_{_sanitize(lbl)}(Context& ctx);")
    else:
        out.append("void run(Context& ctx);")
    out.append("")

    # ---- run() body --------------------------------------------------------
    if has_entries:
        out.append("void run(Context& ctx, EntryPoint entry) {")
        out.append("    switch (entry) {")
        for lbl in entry_labels:
            cpp_lbl = _sanitize(lbl)
            out.append(
                f"        case EntryPoint::ENTRY_{cpp_lbl}: goto _lbl_{cpp_lbl};"
            )
        out.append("        default: break;")
        out.append("    }")
        for instr in instructions:
            out.extend(_emit_instruction_lines(instr, io_lookup, resolved_syms))
        out.append("    return;")
        out.append("}")
    else:
        out.append("void run(Context& ctx) {")
        for instr in instructions:
            out.extend(_emit_instruction_lines(instr, io_lookup, resolved_syms))
        out.append("    return;")
        out.append("}")
    out.append("")

    # ---- Entry wrapper functions -------------------------------------------
    for lbl in entry_labels:
        cpp_name = _sanitize(lbl)
        out.append(f"void run_{cpp_name}(Context& ctx) {{")
        out.append(f"    run(ctx, EntryPoint::ENTRY_{cpp_name});")
        out.append("}")
        out.append("")

    # ---- Footer ------------------------------------------------------------
    out.append(f"constexpr std::uint32_t generated_from_lines = {source_line_count};")
    out.append("")
    out.append("}  // namespace converted")

    return "\n".join(out) + "\n"

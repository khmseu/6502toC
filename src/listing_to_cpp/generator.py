"""Code generator: emit legal C++ from 6502 IR."""

from __future__ import annotations

import re

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_]")

# Mnemonics that read memory into a register (I/O path)
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

# Mnemonics that write a register to memory (I/O path)
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

# Branch mnemonics mapped to their P-flag conditions
_BRANCH_COND: dict[str, str] = {
    "BEQ": "ctx.P & 0x02U",
    "BNE": "!(ctx.P & 0x02U)",
    "BCS": "ctx.P & 0x01U",
    "BCC": "!(ctx.P & 0x01U)",
    "BMI": "ctx.P & 0x80U",
    "BPL": "!(ctx.P & 0x80U)",
    "BVS": "ctx.P & 0x40U",
    "BVC": "!(ctx.P & 0x40U)",
}

# Addressing-mode regexes
_INDIRECT_X_RE = re.compile(r"^\((.+),\s*[Xx]\)$")    # (OP,X)
_INDIRECT_Y_RE = re.compile(r"^\((.+)\),\s*[Yy]$")    # (OP),Y
_INDIRECT_RE   = re.compile(r"^\((.+)\)$")             # (OP)  - JMP indirect
_INDEXED_RE    = re.compile(r"^(.+),\s*([XxYy])\s*$")  # OP,X  OP,Y
_INDEXED_SUFFIX_RE = re.compile(r",\s*([XxYy])\s*$")


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
    """Return a legal C++ uint8 expression for an immediate operand (#...).

    Handles: #<SYM, #>SYM, #$XX, #decimal, #%binary, #SYMBOL.
    Returns None if operand does not start with #.
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

    # Binary literal
    if raw.startswith("%"):
        try:
            return f"0x{int(raw[1:], 2):02X}U"
        except ValueError:
            pass

    # Hex literal
    if raw.startswith("$"):
        try:
            return f"0x{int(raw[1:], 16):02X}U"
        except ValueError:
            pass

    # Decimal literal
    try:
        return f"0x{int(raw):02X}U"
    except ValueError:
        pass

    # Named symbol
    sym = _find_sym_cpp(raw, resolved_syms)
    if sym:
        return f"static_cast<std::uint8_t>({sym})"

    # Unknown identifier - emit as cast; C++ compiler will flag missing names
    return f"static_cast<std::uint8_t>({_sanitize(raw)})"


def _index_register_from_operand(operand: str) -> str | None:
    """Return 'ctx.X' or 'ctx.Y' if operand has an index suffix, else None."""
    m = _INDEXED_SUFFIX_RE.search(operand)
    if m is None:
        return None
    return f"ctx.{m.group(1).upper()}"


def _base_to_addr_cpp(base: str, resolved_syms: dict) -> str:
    """Return a C++ uint16_t expression for a base operand (no index, no parens)."""
    base = base.strip()
    # Hex literal
    if base.startswith("$"):
        try:
            return f"0x{int(base[1:], 16):04X}U"
        except ValueError:
            pass
    # Decimal literal
    try:
        val = int(base)
        return f"0x{val:04X}U"
    except ValueError:
        pass
    # Known EQU symbol
    sym = _find_sym_cpp(base, resolved_syms)
    if sym:
        return f"static_cast<std::uint16_t>({sym})"
    # Unknown - use sanitized name; C++ compile error guides user
    return f"static_cast<std::uint16_t>({_sanitize(base)})"


def _operand_to_addr_expr(operand: str, resolved_syms: dict) -> str:
    """Return a C++ uint16_t address expression for any addressing mode."""
    operand = operand.strip()
    # (OP,X) - indexed indirect
    m = _INDIRECT_X_RE.match(operand)
    if m:
        base = _base_to_addr_cpp(m.group(1), resolved_syms)
        return (
            f"static_cast<std::uint16_t>("
            f"mem_read(static_cast<std::uint16_t>({base} + ctx.X)) | "
            f"mem_read(static_cast<std::uint16_t>({base} + ctx.X + 1U)) << 8)"
        )
    # (OP),Y - indirect indexed
    m = _INDIRECT_Y_RE.match(operand)
    if m:
        base = _base_to_addr_cpp(m.group(1), resolved_syms)
        return (
            f"static_cast<std::uint16_t>("
            f"(mem_read({base}) | mem_read(static_cast<std::uint16_t>({base} + 1U)) << 8) + ctx.Y)"
        )
    # (OP) - indirect
    m = _INDIRECT_RE.match(operand)
    if m:
        base = _base_to_addr_cpp(m.group(1), resolved_syms)
        return (
            f"static_cast<std::uint16_t>("
            f"mem_read({base}) | mem_read(static_cast<std::uint16_t>({base} + 1U)) << 8)"
        )
    # OP,X or OP,Y
    m = _INDEXED_RE.match(operand)
    if m:
        base = _base_to_addr_cpp(m.group(1), resolved_syms)
        reg = f"ctx.{m.group(2).upper()}"
        return f"static_cast<std::uint16_t>({base} + {reg})"
    # Direct
    return _base_to_addr_cpp(operand, resolved_syms)


def _nz(reg: str) -> str:
    """Return a C++ statement that updates N and Z flags from a register/variable."""
    return f"ctx.P = (ctx.P & 0x7DU) | ({reg} & 0x80U) | (!{reg} ? 0x02U : 0U)"


def _emit_implied_line(mnemonic: str, cmt: str) -> str | None:
    """Return a single C++ line for implied-mode instructions, or None."""
    nz_a = _nz("ctx.A")
    nz_x = _nz("ctx.X")
    nz_y = _nz("ctx.Y")
    implied: dict[str, str] = {
        "CLC": f"    ctx.P &= ~0x01U; {cmt}",
        "SEC": f"    ctx.P |= 0x01U; {cmt}",
        "CLD": f"    ctx.P &= ~0x08U; {cmt}",
        "SED": f"    ctx.P |= 0x08U; {cmt}",
        "CLI": f"    ctx.P &= ~0x04U; {cmt}",
        "SEI": f"    ctx.P |= 0x04U; {cmt}",
        "CLV": f"    ctx.P &= ~0x40U; {cmt}",
        "TAX": f"    ctx.X = ctx.A; {nz_x}; {cmt}",
        "TAY": f"    ctx.Y = ctx.A; {nz_y}; {cmt}",
        "TXA": f"    ctx.A = ctx.X; {nz_a}; {cmt}",
        "TYA": f"    ctx.A = ctx.Y; {nz_a}; {cmt}",
        "TSX": f"    ctx.X = ctx.SP; {nz_x}; {cmt}",
        "TXS": f"    ctx.SP = ctx.X; {cmt}",
        "INX": f"    ++ctx.X; {nz_x}; {cmt}",
        "INY": f"    ++ctx.Y; {nz_y}; {cmt}",
        "DEX": f"    --ctx.X; {nz_x}; {cmt}",
        "DEY": f"    --ctx.Y; {nz_y}; {cmt}",
        "PHA": f"    mem_write(0x0100U + ctx.SP--, ctx.A); {cmt}",
        "PHP": f"    mem_write(0x0100U + ctx.SP--, ctx.P); {cmt}",
        "PLA": f"    ctx.A = mem_read(0x0100U + ++ctx.SP); {nz_a}; {cmt}",
        "PLP": f"    ctx.P = mem_read(0x0100U + ++ctx.SP); {cmt}",
    }
    return implied.get(mnemonic)


def _emit_immediate_instr(mnemonic: str, imm: str, cmt: str) -> list[str] | None:
    """Return C++ lines for an instruction with a fully-resolved immediate value."""
    nz_a = _nz("ctx.A")
    nz_x = _nz("ctx.X")
    nz_y = _nz("ctx.Y")
    if mnemonic == "LDA":
        return [f"    ctx.A = {imm}; {nz_a}; {cmt}"]
    if mnemonic == "LDX":
        return [f"    ctx.X = {imm}; {nz_x}; {cmt}"]
    if mnemonic == "LDY":
        return [f"    ctx.Y = {imm}; {nz_y}; {cmt}"]
    if mnemonic == "AND":
        return [f"    ctx.A &= {imm}; {nz_a}; {cmt}"]
    if mnemonic == "ORA":
        return [f"    ctx.A |= {imm}; {nz_a}; {cmt}"]
    if mnemonic == "EOR":
        return [f"    ctx.A ^= {imm}; {nz_a}; {cmt}"]
    if mnemonic == "CMP":
        return [
            f"    {{ std::uint16_t _t = ctx.A - {imm}; "
            f"ctx.P = (ctx.P & 0x7CU) | (_t <= 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U); }} {cmt}"
        ]
    if mnemonic == "CPX":
        return [
            f"    {{ std::uint16_t _t = ctx.X - {imm}; "
            f"ctx.P = (ctx.P & 0x7CU) | (_t <= 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U); }} {cmt}"
        ]
    if mnemonic == "CPY":
        return [
            f"    {{ std::uint16_t _t = ctx.Y - {imm}; "
            f"ctx.P = (ctx.P & 0x7CU) | (_t <= 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U); }} {cmt}"
        ]
    if mnemonic == "ADC":
        return [
            f"    {{ std::uint8_t _s = {imm}; std::uint16_t _t = ctx.A + _s + (ctx.P & 0x01U); "
            f"ctx.P = (ctx.P & 0x3CU) | (_t > 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U) | ((~(ctx.A ^ _s) & (ctx.A ^ _t) & 0x80U) ? 0x40U : 0U); "
            f"ctx.A = static_cast<std::uint8_t>(_t); }} {cmt}"
        ]
    if mnemonic == "SBC":
        return [
            f"    {{ std::uint8_t _s = {imm}; std::uint16_t _t = ctx.A - _s - (1U - (ctx.P & 0x01U)); "
            f"ctx.P = (ctx.P & 0x3CU) | (_t <= 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U) | (((ctx.A ^ _s) & (ctx.A ^ _t) & 0x80U) ? 0x40U : 0U); "
            f"ctx.A = static_cast<std::uint8_t>(_t); }} {cmt}"
        ]
    return None


def _emit_memory_instr(
    mnemonic: str, operand: str, resolved_syms: dict, cmt: str
) -> list[str] | None:
    """Return C++ lines for instructions with a memory (non-immediate) operand."""
    op_upper = operand.strip().upper()
    nz_a = _nz("ctx.A")
    nz_x = _nz("ctx.X")
    nz_y = _nz("ctx.Y")

    # Accumulator shift/rotate (no operand or explicit "A")
    if mnemonic in ("ASL", "LSR", "ROL", "ROR") and op_upper in ("", "A"):
        if mnemonic == "ASL":
            return [
                f"    ctx.P = (ctx.P & 0x7CU) | ((ctx.A & 0x80U) ? 0x01U : 0U); "
                f"ctx.A <<= 1; {nz_a}; {cmt}"
            ]
        if mnemonic == "LSR":
            return [
                f"    ctx.P = (ctx.P & 0x7CU) | (ctx.A & 0x01U); "
                f"ctx.A >>= 1; {nz_a}; {cmt}"
            ]
        if mnemonic == "ROL":
            return [
                f"    {{ std::uint8_t _c = ctx.P & 0x01U; "
                f"ctx.P = (ctx.P & 0x7CU) | ((ctx.A & 0x80U) ? 0x01U : 0U); "
                f"ctx.A = (ctx.A << 1) | _c; {nz_a}; }} {cmt}"
            ]
        if mnemonic == "ROR":
            return [
                f"    {{ std::uint8_t _c = ctx.P & 0x01U; "
                f"ctx.P = (ctx.P & 0x7CU) | (ctx.A & 0x01U); "
                f"ctx.A = (ctx.A >> 1) | (_c << 7); {nz_a}; }} {cmt}"
            ]

    # 65C02 INC/DEC accumulator
    if mnemonic in ("INC", "DEC") and op_upper in ("", "A"):
        op_str = "++" if mnemonic == "INC" else "--"
        return [f"    {op_str}ctx.A; {nz_a}; {cmt}"]

    if not operand.strip():
        return None  # Unknown implied - fall through to stub

    addr = _operand_to_addr_expr(operand, resolved_syms)

    if mnemonic == "LDA":
        return [f"    ctx.A = mem_read({addr}); {nz_a}; {cmt}"]
    if mnemonic == "LDX":
        return [f"    ctx.X = mem_read({addr}); {nz_x}; {cmt}"]
    if mnemonic == "LDY":
        return [f"    ctx.Y = mem_read({addr}); {nz_y}; {cmt}"]
    if mnemonic == "STA":
        return [f"    mem_write({addr}, ctx.A); {cmt}"]
    if mnemonic == "STX":
        return [f"    mem_write({addr}, ctx.X); {cmt}"]
    if mnemonic == "STY":
        return [f"    mem_write({addr}, ctx.Y); {cmt}"]
    if mnemonic == "STZ":
        return [f"    mem_write({addr}, 0U); {cmt}"]
    if mnemonic == "AND":
        return [f"    ctx.A &= mem_read({addr}); {nz_a}; {cmt}"]
    if mnemonic == "ORA":
        return [f"    ctx.A |= mem_read({addr}); {nz_a}; {cmt}"]
    if mnemonic == "EOR":
        return [f"    ctx.A ^= mem_read({addr}); {nz_a}; {cmt}"]
    if mnemonic == "CMP":
        return [
            f"    {{ std::uint16_t _t = ctx.A - mem_read({addr}); "
            f"ctx.P = (ctx.P & 0x7CU) | (_t <= 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U); }} {cmt}"
        ]
    if mnemonic == "CPX":
        return [
            f"    {{ std::uint16_t _t = ctx.X - mem_read({addr}); "
            f"ctx.P = (ctx.P & 0x7CU) | (_t <= 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U); }} {cmt}"
        ]
    if mnemonic == "CPY":
        return [
            f"    {{ std::uint16_t _t = ctx.Y - mem_read({addr}); "
            f"ctx.P = (ctx.P & 0x7CU) | (_t <= 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U); }} {cmt}"
        ]
    if mnemonic == "ADC":
        return [
            f"    {{ std::uint8_t _s = mem_read({addr}); std::uint16_t _t = ctx.A + _s + (ctx.P & 0x01U); "
            f"ctx.P = (ctx.P & 0x3CU) | (_t > 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U) | ((~(ctx.A ^ _s) & (ctx.A ^ _t) & 0x80U) ? 0x40U : 0U); "
            f"ctx.A = static_cast<std::uint8_t>(_t); }} {cmt}"
        ]
    if mnemonic == "SBC":
        return [
            f"    {{ std::uint8_t _s = mem_read({addr}); std::uint16_t _t = ctx.A - _s - (1U - (ctx.P & 0x01U)); "
            f"ctx.P = (ctx.P & 0x3CU) | (_t <= 0xFFU ? 0x01U : 0U) | (_t & 0x80U) | (!(_t & 0xFFU) ? 0x02U : 0U) | (((ctx.A ^ _s) & (ctx.A ^ _t) & 0x80U) ? 0x40U : 0U); "
            f"ctx.A = static_cast<std::uint8_t>(_t); }} {cmt}"
        ]
    if mnemonic == "BIT":
        return [
            f"    {{ std::uint8_t _v = mem_read({addr}); "
            f"ctx.P = (ctx.P & 0x3DU) | (_v & 0xC0U) | (!(ctx.A & _v) ? 0x02U : 0U); }} {cmt}"
        ]
    if mnemonic == "INC":
        return [
            f"    {{ std::uint8_t _v = mem_read({addr}) + 1U; "
            f"mem_write({addr}, _v); {_nz('_v')}; }} {cmt}"
        ]
    if mnemonic == "DEC":
        return [
            f"    {{ std::uint8_t _v = mem_read({addr}) - 1U; "
            f"mem_write({addr}, _v); {_nz('_v')}; }} {cmt}"
        ]
    if mnemonic == "ASL":
        return [
            f"    {{ std::uint8_t _v = mem_read({addr}); "
            f"ctx.P = (ctx.P & 0x7CU) | ((_v & 0x80U) ? 0x01U : 0U); "
            f"_v <<= 1; mem_write({addr}, _v); {_nz('_v')}; }} {cmt}"
        ]
    if mnemonic == "LSR":
        return [
            f"    {{ std::uint8_t _v = mem_read({addr}); "
            f"ctx.P = (ctx.P & 0x7CU) | (_v & 0x01U); "
            f"_v >>= 1; mem_write({addr}, _v); {_nz('_v')}; }} {cmt}"
        ]
    if mnemonic == "ROL":
        return [
            f"    {{ std::uint8_t _c = ctx.P & 0x01U, _v = mem_read({addr}); "
            f"ctx.P = (ctx.P & 0x7CU) | ((_v & 0x80U) ? 0x01U : 0U); "
            f"_v = (_v << 1) | _c; mem_write({addr}, _v); {_nz('_v')}; }} {cmt}"
        ]
    if mnemonic == "ROR":
        return [
            f"    {{ std::uint8_t _c = ctx.P & 0x01U, _v = mem_read({addr}); "
            f"ctx.P = (ctx.P & 0x7CU) | (_v & 0x01U); "
            f"_v = (_v >> 1) | (_c << 7); mem_write({addr}, _v); {_nz('_v')}; }} {cmt}"
        ]
    return None


def _emit_instruction_lines(
    instr: dict,
    io_lookup: dict,
    resolved_syms: dict,
    entry_label_set: set,
) -> list[str]:
    """Return one or more source lines for a single instruction record."""
    mnemonic: str = (instr.get("mnemonic") or "").upper()
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

    # ---- Branch instructions -----------------------------------------------
    cond = _BRANCH_COND.get(mnemonic)
    if cond is not None:
        target = _sanitize(operand) if operand else "_unknown"
        lines.append(f"    if ({cond}) goto _lbl_{target}; {cmt}")
        return lines

    # ---- JMP ---------------------------------------------------------------
    if mnemonic == "JMP":
        m_ind = _INDIRECT_RE.match(operand)
        if m_ind:
            addr_expr = _operand_to_addr_expr(m_ind.group(1), resolved_syms)
            lines.append(
                f"    /* indirect JMP via mem[{addr_expr}] - refactor manually */ {cmt}"
            )
            return lines
        val = _parse_numeric(operand)
        if val is not None or _find_sym_cpp(operand, resolved_syms) is not None:
            lines.append(f"    /* external goto: {operand} */ {cmt}")
        else:
            lines.append(f"    goto _lbl_{_sanitize(operand)}; {cmt}")
        return lines

    # ---- JSR ---------------------------------------------------------------
    if mnemonic == "JSR":
        val = _parse_numeric(operand)
        sym = _find_sym_cpp(operand, resolved_syms)
        if val is not None or sym is not None:
            lines.append(f"    /* external call: {operand} */ {cmt}")
        else:
            lines.append(f"    run_{_sanitize(operand)}(ctx); {cmt}")
        return lines

    # ---- RTS / RTI ---------------------------------------------------------
    if mnemonic == "RTS":
        lines.append(f"    return; {cmt}")
        return lines
    if mnemonic == "RTI":
        lines.append(f"    ctx.P = mem_read(0x0100U + ++ctx.SP); return; {cmt}")
        return lines

    # ---- NOP / BRK ---------------------------------------------------------
    if mnemonic == "NOP":
        lines.append(f"    /* NOP */ {cmt}")
        return lines
    if mnemonic == "BRK":
        lines.append(f"    /* BRK */ {cmt}")
        return lines

    # ---- Implied / register-transfer / stack / flag instructions -----------
    implied = _emit_implied_line(mnemonic, cmt)
    if implied is not None:
        lines.append(implied)
        return lines

    # ---- Immediate operand -------------------------------------------------
    if operand.startswith("#"):
        imm = _emit_immediate_expr(operand, resolved_syms)
        if imm is not None:
            impl = _emit_immediate_instr(mnemonic, imm, cmt)
            if impl is not None:
                lines.extend(impl)
                return lines

    # ---- Memory operand (non-I/O, non-immediate) ---------------------------
    mem_impl = _emit_memory_instr(mnemonic, operand, resolved_syms, cmt)
    if mem_impl is not None:
        lines.extend(mem_impl)
        return lines

    # ---- Default stub: warn at runtime ------------------------------------
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
    entry_label_set: set[str] = set(entry_labels)

    out: list[str] = []

    # ---- File header -------------------------------------------------------
    out.append("// Auto-generated by listing_to_cpp")
    out.append("#include <cstdint>")
    out.append("#include <cstdio>")
    out.append("")
    out.append("namespace converted {")
    out.append("")

    # ---- Shim interface (I/O and general memory) ---------------------------
    out.append("// I/O shim interface (implementation provided by caller)")
    out.append("extern std::uint8_t io_read(std::uint16_t addr);")
    out.append("extern void io_write(std::uint16_t addr, std::uint8_t val);")
    out.append("extern std::uint8_t mem_read(std::uint16_t addr);")
    out.append("extern void mem_write(std::uint16_t addr, std::uint8_t val);")
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
            out.extend(_emit_instruction_lines(instr, io_lookup, resolved_syms, entry_label_set))
        out.append("    return;")
        out.append("}")
    else:
        out.append("void run(Context& ctx) {")
        for instr in instructions:
            out.extend(_emit_instruction_lines(instr, io_lookup, resolved_syms, entry_label_set))
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

from listing_to_cpp.parser import parse_listing


def test_parse_source_include_and_header_markers():
    text = """SOURCE   MAIN.ASM
INCLUDE  MACROS.INC
----- PASS 1 -----
"""

    parsed = parse_listing(text)

    assert parsed["records"] == [
        {
            "type": "source_marker",
            "keyword": "SOURCE",
            "value": "MAIN.ASM",
            "line": 1,
            "raw": "SOURCE   MAIN.ASM",
        },
        {
            "type": "include_marker",
            "keyword": "INCLUDE",
            "value": "MACROS.INC",
            "line": 2,
            "raw": "INCLUDE  MACROS.INC",
        },
        {
            "type": "header_marker",
            "value": "----- PASS 1 -----",
            "line": 3,
            "raw": "----- PASS 1 -----",
        },
    ]


def test_parse_equ_and_equ_alias_lines_with_variable_spacing():
    text = """SCREEN   EQU    $C000
HERE EQU *
"""

    parsed = parse_listing(text)

    assert parsed["records"] == [
        {
            "type": "equ",
            "name": "SCREEN",
            "value": "$C000",
            "is_current_location_alias": False,
            "line": 1,
            "raw": "SCREEN   EQU    $C000",
        },
        {
            "type": "equ",
            "name": "HERE",
            "value": "*",
            "is_current_location_alias": True,
            "line": 2,
            "raw": "HERE EQU *",
        },
    ]


def test_parse_instruction_lines_with_and_without_labels():
    text = """1234  A9 01      START   LDA   #$01   ; init
1236  8D 00 C0             STA   $C000
"""

    parsed = parse_listing(text)

    assert parsed["records"] == [
        {
            "type": "instruction",
            "address": "1234",
            "bytes": ["A9", "01"],
            "label": "START",
            "mnemonic": "LDA",
            "operand": "#$01",
            "comment": "init",
            "line": 1,
            "raw": "1234  A9 01      START   LDA   #$01   ; init",
        },
        {
            "type": "instruction",
            "address": "1236",
            "bytes": ["8D", "00", "C0"],
            "label": None,
            "mnemonic": "STA",
            "operand": "$C000",
            "comment": None,
            "line": 2,
            "raw": "1236  8D 00 C0             STA   $C000",
        },
    ]


def test_parse_data_directives_db_dw_ds_asc_str():
    text = """2000              TABLE   DB   $01,$02,$03
2003                      DW   $1234
2005              BUFFER  DS   16
2015              MSG     ASC  'HELLO'
2020              S       STR  'WORLD'
"""

    parsed = parse_listing(text)

    assert parsed["records"] == [
        {
            "type": "data_directive",
            "address": "2000",
            "label": "TABLE",
            "directive": "DB",
            "operand": "$01,$02,$03",
            "line": 1,
            "raw": "2000              TABLE   DB   $01,$02,$03",
        },
        {
            "type": "data_directive",
            "address": "2003",
            "label": None,
            "directive": "DW",
            "operand": "$1234",
            "line": 2,
            "raw": "2003                      DW   $1234",
        },
        {
            "type": "data_directive",
            "address": "2005",
            "label": "BUFFER",
            "directive": "DS",
            "operand": "16",
            "line": 3,
            "raw": "2005              BUFFER  DS   16",
        },
        {
            "type": "data_directive",
            "address": "2015",
            "label": "MSG",
            "directive": "ASC",
            "operand": "'HELLO'",
            "line": 4,
            "raw": "2015              MSG     ASC  'HELLO'",
        },
        {
            "type": "data_directive",
            "address": "2020",
            "label": "S",
            "directive": "STR",
            "operand": "'WORLD'",
            "line": 5,
            "raw": "2020              S       STR  'WORLD'",
        },
    ]


def test_parse_comment_and_unknown_fallback_lines():
    text = """; file comment
THIS DOES NOT MATCH ANY KNOWN PATTERN
"""

    parsed = parse_listing(text)

    assert parsed["records"] == [
        {
            "type": "comment",
            "comment": "file comment",
            "line": 1,
            "raw": "; file comment",
        },
        {
            "type": "unknown",
            "line": 2,
            "raw": "THIS DOES NOT MATCH ANY KNOWN PATTERN",
        },
    ]


def test_address_prefixed_invalid_mnemonic_falls_back_to_unknown():
    text = "1234  A9 01      START   ZZZ   #$01"

    parsed = parse_listing(text)

    assert parsed["records"] == [
        {
            "type": "unknown",
            "line": 1,
            "raw": "1234  A9 01      START   ZZZ   #$01",
        }
    ]


def test_equ_with_trailing_inline_comment_parses_as_equ():
    text = "SCREEN   EQU    $C000   ; base address"

    parsed = parse_listing(text)

    assert parsed["records"] == [
        {
            "type": "equ",
            "name": "SCREEN",
            "value": "$C000",
            "is_current_location_alias": False,
            "line": 1,
            "raw": "SCREEN   EQU    $C000   ; base address",
        }
    ]


def test_parse_ei_style_addr_colon_lines_for_equ_and_instruction():
    text = """0000:        C000   1 SCREEN                           EQU    $C000
2000:A2 F0          17 L2000                             LDX    #$F0
"""

    parsed = parse_listing(text)

    assert parsed["records"] == [
        {
            "type": "equ",
            "name": "SCREEN",
            "value": "$C000",
            "is_current_location_alias": False,
            "line": 1,
            "raw": "0000:        C000   1 SCREEN                           EQU    $C000",
        },
        {
            "type": "instruction",
            "address": "2000",
            "bytes": ["A2", "F0"],
            "label": "L2000",
            "mnemonic": "LDX",
            "operand": "#$F0",
            "comment": None,
            "line": 2,
            "raw": "2000:A2 F0          17 L2000                             LDX    #$F0",
        },
    ]

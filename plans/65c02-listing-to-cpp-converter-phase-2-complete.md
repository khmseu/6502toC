# Phase 2 Complete: Listing Parser and Line Classification

Phase 2 implemented a tolerant EI-style listing parser that classifies key line categories into structured records and preserves unknown lines safely. The parser now handles header markers, EQU variants (including inline comments), instruction and data-directive lines, plus comment and fallback behavior with regression tests.

**Files created/changed:**

- `src/listing_to_cpp/parser.py`
- `tests/test_parser.py`

**Functions created/changed:**

- `listing_to_cpp.parser.parse_listing`
- `listing_to_cpp.parser._parse_non_listing_line`
- `listing_to_cpp.parser._parse_listing_payload`
- `listing_to_cpp.parser._is_mnemonic`

**Tests created/changed:**

- `tests.test_parser.test_parse_source_include_and_header_markers`
- `tests.test_parser.test_parse_equ_and_equ_current_location_alias`
- `tests.test_parser.test_parse_instruction_with_and_without_label`
- `tests.test_parser.test_parse_data_directives`
- `tests.test_parser.test_parse_comment_and_unknown`
- `tests.test_parser.test_address_prefixed_invalid_mnemonic_falls_back_to_unknown`
- `tests.test_parser.test_equ_with_trailing_inline_comment_parses_as_equ`

**Review Status:** APPROVED

**Git Commit Message:**

feat: add tolerant EI listing parser

- classify listing lines into markers, equ, instruction, data, comment, and unknown
- support EQU aliases and inline-comment tolerant EQU parsing
- add parser tests including invalid mnemonic fallback regression

## Plan: 65C02 Listing to C++ Converter

Build a new command-line converter project in Python that parses 65C02+SWEET16 assembler listings and emits legal C++ code. The design uses a tolerant parser + IR + generator pipeline, enforces library-mediated I/O memory access for explicit addresses in 0xC000-0xCFFF, and supports multi-entry routines with diagnostics for likely code-as-data ambiguity.

**Phases 5**

1. **Phase 1: Project Scaffold and CLI Skeleton**
    - **Objective:** Create a runnable project with package structure, CLI entrypoint, and test harness.
    - **Files/Functions to Modify/Create:** Project root config files, package modules for parser/IR/generator stubs, CLI module, initial tests.
    - **Tests to Write:**
        1. CLI runs with input/output arguments.
        2. Converter loads listing and writes output.
        3. Help and argument error behavior.
    - **Steps:**
        1. Write failing CLI and integration tests first.
        2. Implement minimal CLI and pipeline wiring.
        3. Re-run tests to confirm pass.

2. **Phase 2: Listing Parser and Line Classification**
    - **Objective:** Parse EI-style listing lines into typed records robustly despite spacing/optional fields.
    - **Files/Functions to Modify/Create:** Parser tokenizer/classifier and parsing tests.
    - **Tests to Write:**
        1. SOURCE/INCLUDE/header line parsing.
        2. EQU and EQU * alias parsing.
        3. Instruction parsing with and without labels.
        4. Data directive parsing (DB, DW, DS, ASC, STR).
    - **Steps:**
        1. Add parser tests with EI-like snippets and expected records.
        2. Implement tolerant parsing with fallback unknown records.
        3. Re-run parser tests to confirm pass.

3. **Phase 3: IR and Address Resolution**
    - **Objective:** Build symbol and operand resolution, including explicit C000-CFFF access classification.
    - **Files/Functions to Modify/Create:** IR model, symbol resolver, access policy analyzer, tests.
    - **Tests to Write:**
        1. EQU-based symbol resolution to numeric values.
        2. Explicit direct/symbolic accesses in 0xC000-0xCFFF are detected.
        3. Unresolved indirect accesses are tagged as uncertain warnings.
    - **Steps:**
        1. Write failing resolver and policy tests.
        2. Implement minimal resolver and range classifier.
        3. Re-run tests to confirm pass.

4. **Phase 4: Legal C++ Emission and Multi-Entry Support**
    - **Objective:** Emit compilable legal C++ for parsed instructions/directives with multi-entry routine support.
    - **Files/Functions to Modify/Create:** C++ emitter, symbol sanitizer, runtime shim interfaces, tests.
    - **Tests to Write:**
        1. Generated output has valid C++ scaffolding.
        2. Multiple entry labels generate legal callable entry wrappers or dispatch labels.
        3. Byte-wise operations on word-like symbols produce legal C++ expressions.
    - **Steps:**
        1. Add failing golden-output tests.
        2. Implement emitter logic for supported records.
        3. Re-run tests to confirm pass.

5. **Phase 5: Diagnostics and End-to-End Conversion**
    - **Objective:** Add warnings for likely code-as-data ambiguities and validate conversion flow on sample input.
    - **Files/Functions to Modify/Create:** Diagnostics module, warning reporting in CLI, e2e tests.
    - **Tests to Write:**
        1. Warning on suspicious data-in-code patterns.
        2. Warning on branch/jump target overlap with known data regions.
        3. End-to-end conversion from sample listing to C++ output.
    - **Steps:**
        1. Write failing diagnostics and e2e tests.
        2. Implement warning heuristics and reporting.
        3. Run full suite to confirm pass.

**Open Questions 4**

1. Preferred generated shape: single large function with labels/goto, or split wrappers per entry label to a shared dispatcher?
2. Is C++17 an acceptable minimum target standard?
3. For early SWEET16 support, should unknown SWEET16 ops emit warning comments and stubs instead of hard failure?
4. Should unresolved indirect memory references be warning-only in v1?

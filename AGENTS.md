# Project Instructions (Aetherlink)

## 🛡️ Critical Safety Guardrail

- **Git Safety**: Verify that `.env`, `.cursor/`, and `.agents/` are not staged before any `git push` or `git add`.
- **Secret Scanning**: Block the save and alert the user if an API key is detected in a code block.

## 🏗️ Architectural Boundaries

- **Source Separation**:
  - Python source code lives exclusively in `src/aetherlink/`.
  - Native C++ source code lives in `host/` (headers in `include/`).
- **gRPC Protocol**: The `.proto` files in `proto/` are the authoritative source. Never manually edit generated `*_pb2.py` files.
- **UI**: Always convert `.ui` files using `pyside6-uic` rather than manual coding.

## ✍️ Write Rules

- **Canonical Paths**: If a file exists in multiple locations, update the existing canonical version; do not create duplicates.
- **No Hallucinated Folders**: Do not create `capture_system/`, `engine/`, or `core/` at the root level.
- **Root Files**: Approval is required for any new root-level file other than `PLAN.md` or `PRD.md`.

## 🎨 Project Standards

- **Modern Python**: Use PEP 695 `type Alias = ...` and `int | str` for type hinting.
- **Logging**: Use `loguru` for all logging; never use `print` statements.
- **Testing**: Use `pytest` for all test suites.

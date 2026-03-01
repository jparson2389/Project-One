# Project Instructions (Aetherlink)

## 🛡️ Critical Safety Guardrail

- **Git Context**: Before performing any `git push` or `git add`, verify that `.env`, `.cursor/`, and `.agents/` are not in the staging area.
- **Secret Scanning**: If an API key is detected in a code block, block the save and alert the user.

## 🛠 Environment & Runtime

- **Python**: `3.12`
- **Manager**: [uv](https://github.com/astral-sh/uv)
- **Venv**: Always use `.venv/` (created via `uv sync`).
- **Execution**: Always prefix commands: `uv run <command>`.

## Project Structure & File Locations

- **Rule**: Project structure is authoritative here. Agents must follow this layout even if legacy files exist elsewhere.
- **Separation**:
  - Source structure = development code (agents write here).
  - Automation structure = generated outputs (tools only).
  - Distribution structure = final packaged runtime (zip output).

- **Source (Development)**
  - `src/aetherlink/` → main Python package.
    - `core/` → runtime orchestration, plugin manager, shared logic.
    - `ui/` → PySide6 UI shell and panels.
    - `vision/` → capture + CV interfaces.
    - `input/` → input abstractions.
    - `output/` → output abstractions.
    - `plugins/` → Python plugin interfaces/loaders.
  - `proto/` → `.proto` definitions (authoritative source).
  - `assets/` → icons, themes, UI assets.
  - `include/` → native headers/contracts (if used).
  - `host/` → native host/runtime bridge (if used).
  - `docs/` → documentation.
  - `tests/` → test code.
  - `tools/` → automation scripts and developer tooling.

- **Automation / Generated Output**
  - `state/` → automation state, plan execution data.
  - `logs/` → runtime and automation logs.
  - `build/` → temporary build artifacts.
  - `dist/` → packaging staging output.
  - Agents must NOT create new automation folders outside these.

- **Distribution (Runtime ZIP Layout)**
  - `AetherLink.exe`
  - `lib/`
  - `plugins/`
  - `assets/`
  - `scripts/`
  - This structure is runtime-only. Agents do NOT write here during normal development.

- **Write Rules**
  - All Python source must live under `src/`.
  - Do not create new top-level folders without explicit approval.
  - If a file already exists in multiple locations, do NOT create another copy.
  - Prefer updating canonical paths instead of duplicating files.

- **Forbidden Locations**
  - `.venv/`
  - `__pycache__/`
  - `.pytest_cache/`
  - `.ruff_cache/`
  - Generated protobuf files (`*_pb2.py`, `*_pb2_grpc.py`) should not be manually edited.
  - NO HALLUCINATED FOLDERS: Do not create capture_system/, engine/, core/(at root), protos/(use proto/), or relative/.
  - STRICT SEPARATION: Never write C++(.cpp/.h) files inside the src/ directory. src/ is exclusively for Python(src/aetherlink/).Native plugins go in plugins/ and native headers go in include/.

- **Native Development (C++)**
  - `host/`→ C++ source files (`.cpp`).
  - `include/` → C++ header files (`.h`, `.hpp`).
  - **Rule**: Keep Python and C++ logic strictly decoupled. Communication must happen via gRPC or established C-interfaces.

- **Root-Level Files**
  - Allowed: `pyproject.toml`, `README.md`, `AGENTS.md`, `PLAN.md`, `PRD.md`.
  - Any new root-level file requires explicit approval.

- **Agent Safety**
  - Do not infer structure from accidental or legacy files.
  - Follow AGENTS.md as the single source of truth for structure.

## 🎨 Coding Standards (PEP 8 & 3.12 Syntax)

- **Naming**: `snake_case` (functions/vars), `PascalCase` (classes), `UPPER_SNAKE_CASE` (constants).
- **Typing (Modern)**:
  - Use `type Alias = ...` (PEP 695).
  - Use `int | str` instead of `Union`.
  - Use `list[str]` instead of `List`.
- **Imports**: Standard → Third-party → Local. Use absolute imports only.

## ⚡ Quality Control & Commands

| Task | Command |
| :-- | :-- |
| **Install** | `uv sync` |
| **Format** | `uv run ruff format .` |
| **Lint & Fix** | `uv run ruff check --fix .` |
| **Test** | `uv run pytest` |
| **Clean Cache** | `powershell -Command "Remove-Item -Recurse -Force ./**/__pycache__, ./.pytest_cache, ./.ruff_cache"` |

## 📦 Project Specifics

- **Ignore**: Do not lint/format `*_pb2.py` or `*_pb2_grpc.py`.
- **UI**: Convert `.ui` files using `pyside6-uic`.
- **GRPC**: Generate via `uv run python -m grpc_tools.protoc`.
- **Dependency Rule**: Never manually edit `uv.lock`. Always use `uv add` or `uv remove` to modify dependencies.

## Security & Secrets

- **Zero-Key Policy**: NEVER hardcode API keys, credentials, or tokens.
- **Environment Variables**: Use `python-dotenv` for local development. Always check for `os.getenv()` or `pydantic_settings`.
- **Validation**: If you see a file named `.env`, `secrets.json`, or `.pem`, ensure it is included in `.gitignore` before proceeding with any Git-related automation.
- **Example Files**: When creating new secrets, always generate a corresponding `.env.example` with redacted values.

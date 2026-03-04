# Aetherlink

> Windows-first, plugin-driven controller adapter platform (early development).

`Aetherlink` is a high-performance gaming controller adapter ecosystem built
around a microkernel-style host. It combines native plugin contracts, a Python
runtime, and a PySide6 UI shell to support low-latency input/output workflows,
capture pipelines, and worker-based processing.

## What This Project Does

- Provides a plugin-oriented runtime model for controller, capture, and worker
  features.
- Defines core contracts for plugin identity, lifecycle, and capabilities.
- Implements shared-memory frame layout primitives for deterministic data
  transport.
- Includes a basic Python entrypoint and an initial PySide6 main window shell.

## Why Aetherlink Is Useful

- **Clear architecture boundaries**: plugin ABI and shared-memory contracts are
  explicitly modeled and tested.
- **Windows-focused stack**: Python 3.12 + PySide6 + native plugin direction.
- **Developer-first workflow**: `uv` package management, `ruff`, and `pytest`
  are configured out of the box.
- **Incremental implementation plan**: architecture and roadmap docs are
  already included for contributors.

## Project Layout

```text
src/aetherlink/
  core/                 Core runtime and layout contracts
  input/                Input plugin surfaces
  plugins/              Plugin interfaces and loader stubs
  ui/                   PySide6 UI shell
  main.py               CLI/gui entrypoint
tests/                  Top-level test suite
docs/architecture/      Architecture and design docs
PRD.md                  Product requirements
PLAN.md                 Implementation roadmap
```

## Getting Started

### Prerequisites

- Windows 11 (project is currently scoped to Windows v1)
- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) installed
- PowerShell (recommended shell for this repository)

### Install

```powershell
uv sync
```

### Run

CLI entrypoint:

```powershell
uv run aetherlink
```

GUI script entrypoint:

```powershell
uv run aetherlink-gui
```

## Usage Examples

Build and validate a shared-memory frame ring layout:

```python
from aetherlink.core.shared_memory_layout import build_layout

layout = build_layout(
    width=1280,
    height=720,
    pixel_format="BGRA32",
    slot_count=3,
)

slot_stride = layout.header.slot_stride_bytes
first_offset = layout.slots[0].offset_bytes  # 0
```

Inspect remote-play plugin metadata:

```python
from aetherlink.core.remote_play import RemotePlayPlugin

plugin = RemotePlayPlugin(services={})
capabilities = plugin.get_capabilities()
```

## Development Workflow

Run quality checks:

```powershell
uv run ruff check .
uv run pytest
```

Run formatting:

```powershell
uv run ruff format .
```

## Help and Documentation

- Architecture overview: [`docs/architecture/system_overview.md`](docs/architecture/system_overview.md)
- Plugin ABI details: [`docs/architecture/plugin_abi.md`](docs/architecture/plugin_abi.md)
- Shared memory layout notes: [`docs/architecture/shared_memory_layout.md`](docs/architecture/shared_memory_layout.md)
- Product requirements: [`PRD.md`](PRD.md)
- Implementation plan: [`PLAN.md`](PLAN.md)

If you find a bug or need clarification, open an issue in this repository with:
- your OS and Python version
- the command you ran
- full error output

## Maintainers and Contributions

This project is maintained by Aetherlink contributors.

Contributions are welcome. For now:
- follow `AGENTS.md` for project guardrails and workflow constraints
- keep changes scoped and test-backed
- include relevant tests with behavioral changes

If a dedicated `CONTRIBUTING.md` is added later, it should become the canonical
contribution guide referenced here.

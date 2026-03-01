# Implementation Plan — Windows v1

## Executive Overview

This document defines the complete implementation plan for a Windows-first, plugin-driven controller adapter ecosystem.

The system is built on a microkernel host architecture where all major functionality is delivered through signed plugins, with strict separation between sensing, acting, runtime isolation, and entitlement enforcement.

Platform: Windows only UI: Qt for Python (PySide6 6.9.x) Runtime: Native C++20 plugins + out-of-process Python workers IPC: gRPC (control plane) + shared memory (data plane) Monetization: Tiered entitlements with premium plugin gating

---

# System Architecture

## Architectural Principles

1. Microkernel host with strict plugin boundaries
2. Deterministic input → mapping → output pipeline
3. Capability-based hardware exposure
4. Out-of-process execution for Python runtime
5. Entitlement enforcement at load boundary
6. Signed artifact and plugin trust enforcement

---

# Agent Structure (5-Agent Model)

## 1. Core Runtime Architect

### Responsibilities

- Define and maintain plugin ABI (C++20 + C boundary)
- Plugin loader with signature verification
- Entitlement enforcement at plugin load path
- Deterministic mapping engine
- Shared memory frame ring buffer schema
- Performance instrumentation

### Required Tooling

- C++20 toolchain
- Authenticode verification
- ABI compatibility validation
- Static analysis and profiling tools

### Performance Targets

- Input → Output overhead <5ms typical
- Plugin load <200ms
- 100% signature enforcement
- Zero ABI regressions in CI

---

## 2. UX & Host Shell (PySide6)

### Responsibilities

- Qt shell and plugin-driven panel system
- Capture configuration UI
- Mode matrix filtering (FPS + resolution)
- Premium lock states
- Worker health HUD
- Environment manager interface
- Resource installation flows

### Required Tooling

- PySide6 6.9.x
- Async orchestration
- UI integration testing
- Telemetry instrumentation

### Performance Targets

- No UI blocking >16ms
- First-run → baseline mapping ≤5 minutes
- Accurate capture mode filtering
- Premium plugins non-selectable while locked

---

## 3. Native I/O & Capture Systems

### Responsibilities

- Capture plugins (OpenCV default)
- Premium capture backends (locked until entitlement)
- Capability matrix generation
- Device enumeration with stable identifiers
- Input device plugins
- Virtual controller output integration
- CPU and GPU render panel plugins

### Required Tooling

- Windows Media Foundation
- DirectShow (legacy support)
- OpenCV
- DXGI / OpenGL interop
- Windows device APIs

### Performance Targets

- Stable 60 FPS baseline ≥95% sessions
- Accurate runtime mode matrix
- FPS deviation <5%
- Graceful backend fallback ≥99%

---

## 4. Runtime Services & Isolation

### Responsibilities

- Python worker supervisor
- gRPC control plane
- Shared memory frame transport
- uv environment lifecycle management
- Environment bundle installation
- Artifact verification (SHA-256 + signature)
- Resource catalog client

### Required Tooling

- uv CLI automation
- gRPC (Python + C++ bindings)
- Shared memory primitives
- Cryptographic validation library
- Structured logging system

### Performance Targets

- Worker restart <3s
- Host survivability ≥99.9%
- Bundle install success ≥95%
- No unsigned artifact execution

---

## 5. Platform & Entitlements

### Responsibilities

- Authentication integration
- Entitlement state machine
- Offline grace TTL enforcement
- Premium gating coordination
- Admin API services
- Manifest and artifact distribution
- CI contract enforcement
- Release validation automation

### Required Tooling

- OAuth provider SDK
- JWT validation
- Cloud-based artifact storage
- CI/CD with contract validation
- Automated regression + performance suites

### Performance Targets

- Entitlement refresh <500ms
- Offline grace accuracy 100%
- Zero unauthorized premium activation
- 100% regression suite pass rate before release

---

# Milestone Roadmap

## Phase 0 — Core Architecture & Boundaries

- [ ] Deviation Remediation: Resolve placeholder files for remote-play and GPU renderer

  > **Target Files:** `src/aetherlink/plugins/capture/_stubs/test_plugin_stubs.py` **Test File:** `tests/test_no_placeholders.py` **Behavior:** Address the feature creep deviation where placeholder files exist but lack concrete implementation for remote-play and GPU visualization. **Validation:** Ensure no missing plugin implementions masquerade as completed logic. **Process:** TDD REQUIRED.

- [ ] Block: Implement remote-play integration with plugin system

  > **Target Files:** `src/aetherlink/core/remote_play.py` **Test File:** `tests/test_remote_play.py` **Behavior:** Fulfills the missing PRD requirement of remote-play integration. **Validation:** Integration tests must verify functionality. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Block: Complete GPU renderer plugin

  > **Target Files:** `src/aetherlink/plugins/capture/gpu_renderer.py` **Test File:** `tests/test_gpu_renderer_plugin.py` **Behavior:** Replaces the GPU renderer placeholder with concrete implementation. **Validation:** Test that the pipeline handles output without crashing. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Block: Add dependency tracking for environment management

  > **Target Files:** `src/aetherlink/core/env_manager.py` **Test File:** `tests/test_dependency_tracking.py` **Behavior:** Tracks dependency count and disk usage for the environment manager. **Validation:** Validates disk usage and package tracking is emitted. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Block: Integrate admin dashboard UI elements

  > **Target Files:** `src/aetherlink/ui/panels/admin_dashboard.py` **Test File:** `tests/test_admin_dashboard.py` **Behavior:** Integrate the entitlement and grace period logic into a concrete UI Admin Dashboard panel. **Validation:** Ensure modal elements launch and show mocked entitlement data. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Freeze plugin ABI

  > **Target File:** `src/aetherlink/plugins/include/plugin_system.hpp` **Test File:** `tests/test_plugin_abi.cpp` **Behavior:** Defines strict C-ABI boundaries for native plugins. Must include structs for PluginIdentity, Capabilities, and Lifecycle hooks. **Validation:** File must exist, compile (if tested against dummy C++ file), and not rely on Python objects. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Freeze gRPC proto

  > **Target File:** `src/aetherlink/proto/capture.proto` **Test File:** `tests/test_capture_proto.py` **Output Files:** `src/aetherlink/proto/capture_pb2.py`, `src/aetherlink/proto/capture_pb2_grpc.py` **Behavior:** Defines gRPC services for worker control. Separates control plane messages from data payloads. **Validation:** `uv run python -m grpc_tools.protoc` completes successfully and produces the output Python files. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Define shared memory layout contract

  > **Target File:** `src/aetherlink/core/shared_memory_layout.py` **Test File:** `tests/test_shared_memory_layout.py` **Behavior:** Deterministic ring buffer layout defined and validated in Python. **Validation:** `uv run pytest tests/test_shared_memory_layout.py` must pass with 0 errors. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

---

## Phase 1 — UI Shell & Core Framework

- [ ] Deviation Remediation: Sweep and isolate plugin placeholders

  > **Target Files:** `src/aetherlink/plugins/capture/_stubs/*` **Behavior:** Audit the plugin stubs path to either fully implement or remove dummy files so they do not masquerade as completed logic. **Validation:** `ls src/aetherlink/plugins/capture/_stubs/` must contain no untracked dangling logic schemas. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Deviation Remediation: Isolate or Sequence Offline Grace logic

  > **Target Files:** `src/aetherlink/core/grace_period.py` **Test File:** `tests/test_grace_period.py` **Behavior:** Formalize the partially implemented offline grace logic or revert it until Phase 4 prerequisites are met. **Validation:** `uv run pytest tests/test_grace_period.py` must reliably test the expiry TTL of the entitlement object. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Block: Implement remote-play integrations

  > **Target Files:** `src/aetherlink/core/remote_play.py` **Test File:** `tests/test_remote_play.py` **Behavior:** Python module linking remote-play integrations to the core pipeline. **Validation:** `uv run pytest tests/test_remote_play.py` ensures the module is importable and interfaces are defined. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Block: Complete scripting and inference engine plugins

  > **Target Files:** `src/aetherlink/plugins/inference_engine.py` **Test File:** `tests/test_inference_engine.py` **Behavior:** Implements the scripting and ML inference plugin abstractions. **Validation:** `uv run pytest tests/test_inference_engine.py` verifies plugin registration behavior. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Block: Optimize GPU rendering support

  > **Target Files:** `src/aetherlink/plugins/capture/gpu_renderer.py` **Test File:** `tests/test_gpu_renderer.py` **Behavior:** Replaces the GPU renderer stub with a functional implementation. **Validation:** `uv run pytest tests/test_gpu_renderer.py` ensures the rendering pipeline does not crash under test loads. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Block: Test and validate all subsystem interactions

  > **Target Files:** `tests/integration/test_subsystems.py` **Test File:** `tests/integration/test_subsystems.py` **Behavior:** End-to-end integration tests spanning capture, input, and outputs. **Validation:** `uv run pytest tests/integration/test_subsystems.py` passing with 0 errors. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Deliver basic PySide6 Qt shell

  > **Target Files:** `src/aetherlink/main.py`, `src/aetherlink/ui/main_window.py` **Test File:** `tests/test_ui_shell.py` **Behavior:** `aetherlink/main.py` properly initializes `QApplication` and creates an instance of `MainWindow`. Uses proper PySide6 imports and `app.exec()`. **Validation:** `uv run pytest tests/test_ui_shell.py` must mock the exec loop and assert `QApplication` initialization does not crash, and `MainWindow` can be instantiated. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Implement baseline input and output plugins contract

  > **Target Files (Python):** `src/aetherlink/input/xinput.py`, `src/aetherlink/output/vigem.py` **Target Files (Native):** `host/plugins/xinput_provider.cpp`, `host/plugins/vigem_output.cpp` **Test File:** `tests/test_io_plugins.py` **Behavior:** Python files must define abstract interfaces for reading/writing controller state. Native files must provide C++ stub implementations exporting the `Initialize` and `GetCapabilities` functions defined in `plugin_system.hpp`. **Validation:** Python interfaces must be importable (`python -c "import aetherlink.input.xinput"`). **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

---

## Phase 2 — Capture + Worker Integration

- [ ] Deliver OpenCV capture plugin contract

  > **Target File (Python):** `src/aetherlink/vision/cv_capture.py` **Target File (Native):** `host/plugins/cv_capture.cpp` **Test File:** `tests/test_cv_capture.py` **Behavior:** Python module outlines interaction with the native CV capture plugin. Native plugin must stub frame capture logic and shared memory mapping. **Validation:** Python integration test must be written to verify module import and method signatures. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Implement capability matrix filtering contract

  > **Target Files:** `host/capability_matrix_filtering.cpp`, `include/capability_matrix_filtering.h` **Test File:** `tests/test_capability_matrix.cpp` **Behavior:** Host parsing logic to reject plugin capabilities that do not match the expected schema. **Validation:** Must compile alongside the host application. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Implement worker supervisor + IPC

  > **Target Files:** `host/worker_supervisor.cpp`, `src/aetherlink/core/supervisor.py` **Test File:** `tests/test_supervisor.py` **Behavior:** Logic to start, monitor (heartbeat), and cleanly stop a Python worker process via subprocess injection and gRPC. **Validation:** Pytest `tests/test_supervisor.py` demonstrating process spawn and termination. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Add performance HUD panel

  > **Target File:** `src/aetherlink/ui/panels/performance_hud.py` **Test File:** `tests/test_performance_hud.py` **Behavior:** PySide6 widget rendering real-time FPS, latency, and resource metrics. **Validation:** Unit test verifying widget instantiation and default text values. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

---

## Phase 3 — Environment + Resource System

- [ ] Implement uv environment management contract

  > **Target File:** `src/aetherlink/core/env_manager.py` **Test File:** `tests/test_env_manager.py` **Behavior:** Programmatically creates isolated `.venv` directories utilizing `uv` underneath. **Validation:** Pytest script that mocks a `subprocess.run` call to verify `uv venv` bounds are commanded correctly. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Deliver environment bundle installer contract

  > **Target File:** `src/aetherlink/core/bundle_installer.py` **Test File:** `tests/test_bundle_installer.py` **Behavior:** Extracts a zipped resource bundle and verifies a mock `manifest.json`. **Validation:** Pytest using `tempfile` and `zipfile` to simulate extraction and verify paths. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Implement signed artifact verification contract

  > **Target Files:** `host/artifact_verifier.cpp`, `src/aetherlink/core/security.py` **Test File:** `tests/test_security.py` **Behavior:** Enforces SHA-256 and signature checks. **Validation:** Unit tests for Python security logic simulating both valid and mismatch hashes. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Add resource browsing UI panel

  > **Target File:** `src/aetherlink/ui/panels/online_resources.py` **Test File:** `tests/test_online_resources.py` **Behavior:** PySide6 modal bridging catalog metadata into a visual list. **Validation:** Pytest assessing UI logic with mock JSON responses. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

---

## Phase 4 — Entitlements + Admin

- [ ] Implement entitlement validation contract

  > **Target File:** `src/aetherlink/core/entitlements.py` **Target File (Native):** `host/entitlement_check.cpp` **Test File:** `tests/test_entitlement_check.py` **Behavior:** Validates JWT/Local Cache for Tier assignments. **Validation:** Tests utilizing a mocked JWT payload. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Implement premium plugin gating contract

  > **Target Files (Native):** Updates to `host/plugin_loader.cpp` **Test File:** `tests/test_plugin_loader.cpp` **Behavior:** Refuses to map premium DLLs into memory without entitlement. **Validation:** Test verifying a premium DLL fails to load without a token and routes to a simulated purchase flow. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Deliver admin APIs contract

  > **Target File:** `src/aetherlink/core/admin_api.py` **Test File:** `tests/test_admin_api.py` **Behavior:** Exposes mock REST/RPC endpoints for remote diagnostics. **Validation:** Test invoking defined endpoints to assert standardized JSON returns. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

- [ ] Implement offline grace logic contract

  > **Target File:** `src/aetherlink/core/grace_period.py` **Test File:** `tests/test_grace_period_logic.py` **Behavior:** Caches state with TTL. Upon expiry, premium features lock. **Validation:** Time-travel unit test proving TTL expiry drops entitlement correctly. **Process:** TDD REQUIRED. You MUST write the test first, execute it to prove it fails, write the implementation code, and execute it again to prove it passes.

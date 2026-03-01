# Implementation Plan — Windows v1

## Executive Overview

This document defines the complete implementation plan for a Windows-first, plugin-driven controller adapter ecosystem.

The system is built on a microkernel host architecture where all major functionality is delivered through signed plugins, with strict separation between sensing, acting, runtime isolation, and entitlement enforcement.

Platform: Windows only  
UI: Qt for Python (PySide6 6.9.x)  
Runtime: Native C++20 plugins + out-of-process Python workers  
IPC: gRPC (control plane) + shared memory (data plane)  
Monetization: Tiered entitlements with premium plugin gating

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

- Freeze plugin ABI

### Freeze plugin ABI

Deliverables: `include/plugin_system.hpp`  
Behavior: Defines strict C-ABI boundaries for native plugins.  
Tests: Minimal compile test asserting ABI boundaries.  
Evidence: Verified existence of `include/plugin_system.hpp`.

- Freeze gRPC proto

### Freeze gRPC proto

Deliverables: `proto/capture.proto`  
Behavior: Strictly separates control plane messages from data payloads.  
Tests: `protoc` compiles successfully for both C++ and Python targets.  
Evidence: Verified existence of `proto/capture.proto`.

- Define shared memory layout

### Define shared memory layout

Deliverables: `docs/architecture/shared_memory_layout.md`, `src/aetherlink/core/shared_memory_layout.py`  
Behavior: Deterministic ring buffer layout defined and validated in Python.  
Tests: `tests/test_shared_memory_layout.py` passes.  
Evidence: Passing pytest in CI.

Exit Criteria:

All contracts versioned and validated in CI

---

## Phase 1 — UI Shell & Core Framework

- Deliver basic PySide6 shell

### Deliver basic PySide6 shell

Deliverables: `src/aetherlink/main.py`, `src/aetherlink/ui/main_window.py`  
Behavior: `uv run aetherlink` launches a PySide6 application window.  
Tests: Pytest asserting `QApplication` initialization without crashing.  
Evidence: Passing test logs for UI initialization.

- Implement baseline input and output plugins

### Implement baseline input and output plugins

Deliverables: `plugins/xinput_provider.cpp`, `plugins/vigem_output.cpp`, `src/aetherlink/input/xinput.py`, `src/aetherlink/output/vigem.py`  
Behavior: Translates native XInput events to ViGEm virtual outputs.  
Tests: Script simulating button presses and asserting output changes.  
Evidence: Integration test logs showing input-to-output translation.

Exit Criteria:

Deterministic mapping working end-to-end

---

## Phase 2 — Capture + Worker Integration

- Deliver OpenCV capture plugin

### Deliver OpenCV capture plugin

Deliverables: `plugins/cv_capture.cpp`, `src/aetherlink/vision/cv_capture.py`  
Behavior: Captures video frames and copies to shared memory.  
Tests: Native test capturing frames and asserting timestamp consistency.  
Evidence: Native plugin code and performance test logs.

- Implement capability matrix filtering

### Implement capability matrix filtering

Deliverables: `host/capability_filtering.cpp`, `include/capability_matrix_filtering.h`  
Behavior: System rejects plugins that lack required capability schemas.  
Tests: Unit tests loading valid and invalid capability matrices.  
Evidence: Test suite output proving rejection of invalid matrices.

- Implement worker supervisor + IPC

### Implement worker supervisor + IPC

Deliverables: `host/worker_supervisor.cpp`, `src/aetherlink/core/supervisor.py`  
Behavior: Host launches, monitors, and cleanly tears down Python workers.  
Tests: Test intentionally crashing the worker, asserting host survives.  
Evidence: Crash-recovery test logs.

- Add performance HUD

### Add performance HUD

Deliverables: `src/aetherlink/ui/panels/performance_hud.py`  
Behavior: Renders real-time FPS, latency, and resource metrics.  
Tests: Pytest asserting metric updates reflect in the Qt models.  
Evidence: Test output proving model updates.

Exit Criteria:

Stable 60 FPS baseline  
Host survives worker crash scenarios

---

## Phase 3 — Environment + Resource System

- Implement uv environment management

### Implement uv environment management

Deliverables: `src/aetherlink/core/env_manager.py`  
Behavior: Programmatically creates isolated `.venv` directories.  
Tests: Pytest script that creates a temp env and installs a package.  
Evidence: Passing test logs for environment creation.

- Deliver environment bundle installer

### Deliver environment bundle installer

Deliverables: `src/aetherlink/core/bundle_installer.py`  
Behavior: Extracts a zipped resource bundle and verifies its manifest.  
Tests: End-to-end test compressing and installing a mock bundle.  
Evidence: E2E test output proving extraction.

- Implement signed artifact verification

### Implement signed artifact verification

Deliverables: `host/artifact_verifier.cpp`, `src/aetherlink/core/security.py`  
Behavior: Enforces signature checks before executing downloaded plugins.  
Tests: Attempting to load an unsigned dummy DLL fails securely.  
Evidence: Security test logs proving unsigned rejection.

- Add resource browsing and install UI

### Add resource browsing and install UI

Deliverables: `src/aetherlink/ui/panels/online_resources.py`  
Behavior: Modal fetching catalog metadata and providing install progress.  
Tests: Mock network request returning catalog JSON.  
Evidence: Mock network test logs.

Exit Criteria:

Script/model install + worker execution functional

---

## Phase 4 — Entitlements + Admin

- Implement entitlement validation

### Implement entitlement validation

Deliverables: `host/entitlement_check.cpp`, `src/aetherlink/core/entitlements.py`  
Behavior: Validates local cache or remote server tokens for user tier.  
Tests: Mock server responses testing token validation.  
Evidence: Unit test output for token verification.

- Implement premium plugin gating

### Implement premium plugin gating

Deliverables: Updates to `host/plugin_loader.cpp`  
Behavior: Refuses to map premium DLLs into memory without entitlement.  
Tests: Loading a premium DLL without a token routes to purchase flow.  
Evidence: Gating test logs.

- Deliver admin APIs

### Deliver admin APIs

Deliverables: `src/aetherlink/core/admin_api.py`  
Behavior: Exposes endpoints for remote diagnostics and telemetry.  
Tests: Pytest invoking admin commands and asserting JSON responses.  
Evidence: Endpoint test logs.

- Implement offline grace logic

### Implement offline grace logic

Deliverables: `src/aetherlink/core/grace_period.py`  
Behavior: Caches state with TTL. Upon expiry, premium features lock.  
Tests: Time-travel test proving TTL expiry locks plugins.  
Evidence: Time-travel test output.

Exit Criteria:

Premium plugins unlock without reinstall  
Expired entitlements relock correctly

---

# Security & Reliability Requirements

All plugins must be signed  
Premium plugins not loadable without entitlement  
Worker crashes must not affect host  
Artifact integrity verified before execution  
Capability matrices generated dynamically  
All entitlement checks enforced at runtime boundary

---

# Release Readiness Requirements

Performance regression tests pass  
ABI compatibility checks pass  
Artifact integrity validation passes  
Installer + updater validation complete  
Diagnostics export functional

---

# Success Metrics

Install → working baseline ≤5 minutes median  
60 FPS stability ≥95%  
Host crash rate <0.1%  
Environment bundle success ≥95%  
Zero premium bypass incidents

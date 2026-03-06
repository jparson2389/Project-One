# Implementation Plan — Aetherlink

Grounded in `PRD.md` and `AGENTS.md`. Every path verified against project
structure. No agent may modify this plan without human sign-off.

---

## Rules For Agents Reading This Plan

- **Frozen contracts:** `include/plugin_system.hpp`, `proto/capture.proto`,
  `src/aetherlink/core/shared_memory_layout.py` — do NOT modify these.
- **TDD is mandatory:** write the test first, prove it fails, implement, prove
  it passes. Do not mark done without a passing `uv run pytest` run.
- **No `_stubs/` directories** anywhere in the repo. Ever.
- **No C++ files inside `src/`** — C++ lives in `host/` and `include/` only.
- **No `assert True` tests** — every test must make a real assertion.
- **No placeholder code** — no `pass # TODO`, no `# Add implementation here`.
- **All Python** must have type hints and Google-format single-quoted docstrings.
- **Target paths are canonical** — do not invent new paths or directories.

---

## Atomic Recovery Protocol (ARP)

If any validation command exits non-zero:

1. **CAPTURE:** `git diff > _recovery/failed_state_<timestamp>.patch`
2. **ANALYZE:** `uv run ruff check <failing_file>` and
   `uv run pytest <failing_test> -vv`
3. **REPORT:** "Validation failed because: `<reason>`. Affected file: `<path>`."
4. **FIX:** One minimal fix attempt only.
5. **REVERT:** If fix fails, `git checkout -- <files>`, report BLOCKED.

Every work item that has a validation command implicitly triggers ARP on
non-zero exit. Agents must not skip to the next retry without executing
steps 1–3 first.

---

## Phase 0 — Frozen Contracts & Core Boundaries

Goal: establish the contracts that everything else builds on. Nothing in Phase
1+ may proceed until these are locked and tested.

### Work Items

- [x] Freeze plugin ABI contract
  `[ABI-FRZ-01] -> [PRD-§5.1.2, §4.4]`
  > **Target File:** `include/plugin_system.hpp`
  > **Behavior:** C-ABI plugin lifecycle and capability contract. Frozen.
  > **Validation:** `uv run pytest tests/test_plugin_abi.py -vv`
  > **Evidence:** File exists at `include/plugin_system.hpp`
  > **ARP Trigger:** Any modification to this file requires a breaking-change
  > log entry at `docs/breaking-changes/abi.md` before proceeding.

- [x] Freeze gRPC capture proto
  `[IPC-FRZ-01] -> [PRD-§5.9, §4.4]`
  > **Target File:** `proto/capture.proto`
  > **Output Files:** `src/aetherlink/proto/capture_pb2.py`,
  > `src/aetherlink/proto/capture_pb2_grpc.py`
  > **Behavior:** Control-plane gRPC contract for worker management. Frozen.
  > **Validation:**
  > `uv run python -m grpc_tools.protoc -I proto/ --python_out=src/aetherlink/proto/ --grpc_python_out=src/aetherlink/proto/ proto/capture.proto`
  > **Evidence:** Both pb2 files exist and import without errors.
  > **ARP Trigger:** Report exact protoc error before any fix attempt.

- [x] Define shared memory layout contract
  `[IPC-SHM-01] -> [PRD-§5.9, §4.4]`
  > **Target File:** `src/aetherlink/core/shared_memory_layout.py`
  > **Test File:** `tests/test_shared_memory_layout.py`
  > **Behavior:** Deterministic 64-byte-aligned ring buffer layout. Frozen.
  > **Validation:** `uv run pytest tests/test_shared_memory_layout.py -vv`
  > **Evidence:** All layout offset and alignment assertions pass.
  > **ARP Trigger:** Report the failing offset assertion and expected vs actual
  > values before any fix attempt.

- [ ] Implement Python plugin ABI mirror
  `[ABI-PY-01] -> [PRD-§5.1.2]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target File:** `src/aetherlink/plugins/plugin_interface.py`
  > **Test File:** `tests/test_plugin_interface.py`
  > **Behavior:** Python ABC mirroring the C-ABI contract from
  > `include/plugin_system.hpp`. Must define: `initialize`, `start`, `stop`,
  > `shutdown`, `get_capabilities`, `required_entitlements`, `requires_worker`.
  > Instantiating the ABC directly must raise `TypeError`.
  > **Validation:** `uv run pytest tests/test_plugin_interface.py -vv`
  > **Evidence:** ABC enforcement test passes; all abstract methods verified.
  > **ARP Trigger:** Report which abstract method is missing or has the wrong
  > signature before any fix attempt.

- [ ] Implement plugin loader
  `[ABI-LDR-01] -> [PRD-§5.1.4, §4.1]`
  > **Preconditions:** `[ABI-PY-01]` complete
  > **Target File:** `src/aetherlink/plugins/plugin_loader.py`
  > **Test File:** `tests/test_plugin_loader.py`
  > **Behavior:** Loads a `PluginInterface` subclass from a given module path.
  > Validates ABI compatibility before returning. Raises `PluginLoadError` on
  > unsigned, incompatible, or missing plugins.
  > **Validation:** `uv run pytest tests/test_plugin_loader.py -vv`
  > **Evidence:** Load success and `PluginLoadError` paths both asserted.
  > **ARP Trigger:** Report which load path failed and the exact exception
  > before any fix attempt.

- [ ] Implement service container
  `[ABI-SVC-01] -> [PRD-§4.1]`
  > **Preconditions:** None
  > **Target File:** `src/aetherlink/plugins/service_container.py`
  > **Test File:** `tests/test_service_container.py`
  > **Behavior:** Typed registry for host services (logging, config, auth,
  > telemetry). `register(name, instance)` and `get(name)` with `KeyError` on
  > missing. Must use type hints throughout.
  > **Validation:** `uv run pytest tests/test_service_container.py -vv`
  > **Evidence:** Register, get, and missing-key assertions all pass.
  > **ARP Trigger:** Report which assertion failed and the actual return value
  > before any fix attempt.

- [ ] Prove no placeholder code exists in src/
  `[ABI-DEV-01] -> [PRD-§4.4]`
  > **Target File:** `tests/test_no_placeholders.py`
  > **Behavior:** Scanner test that fails if any `src/` Python file contains
  > `assert True`, `pass  # TODO`, or `# Add your implementation here`. Also
  > fails if any test file contains `assert True`.
  > **Validation:** `uv run pytest tests/test_no_placeholders.py -vv`
  > **Evidence:** 2 tests pass, 0 failures.
  > **ARP Trigger:** Report the exact file and pattern that triggered the
  > failure. Delete the offending file or fix the pattern — do not suppress
  > the scanner.

### Phase 0 Exit Criteria

```bash
uv run pytest tests/test_shared_memory_layout.py
uv run pytest tests/test_plugin_interface.py
uv run pytest tests/test_plugin_loader.py
uv run pytest tests/test_service_container.py
uv run pytest tests/test_no_placeholders.py
uv run ruff check . && uv run pytest tests/ -x
```

All 6 commands must exit 0 before Phase 1 begins.

---

## Phase 1 — UI Shell & Core Framework

Goal: a working application shell that boots, shows a window, and routes to
plugin-backed panels.

### Work Items

- [ ] Deliver PySide6 Qt shell
  `[UI-SHL-01] -> [PRD-§6]`
  > **Preconditions:** Phase 0 exit criteria passed
  > **Target Files:** `src/aetherlink/main.py`,
  > `src/aetherlink/ui/main_window.py`
  > **Test File:** `tests/test_ui_shell.py`
  > **Behavior:** `QApplication` and `MainWindow` initialize without error.
  > Dark theme with purple accents applied. Status bar visible. No Qt warnings
  > on stderr.
  > **Validation:** `uv run pytest tests/test_ui_shell.py -vv`
  > **Evidence:** `MainWindow` instantiation assertion passes headlessly via
  > offscreen platform.
  > **ARP Trigger:** Report exact Qt binding error or missing import before any fix attempt.

- [ ] Implement XInput plugin contract
  `[ABI-IO-01] -> [PRD-§5.2, §5.6]`
  > **Preconditions:** `[ABI-PY-01]` complete
  > **Target File:** `src/aetherlink/input/xinput.py`
  > **Test File:** `tests/test_xinput.py`
  > **Behavior:** Concrete `PluginInterface` subclass for XInput-class
  > controllers. `read_controller_state()` returns typed dict.
  > `get_capabilities()` returns valid mode matrix.
  > **Validation:** `uv run pytest tests/test_xinput.py -vv`
  > **Evidence:** All interface method assertions pass.
  > **ARP Trigger:** Report which interface method returned the wrong type
  > or raised unexpectedly before any fix attempt.

- [ ] Implement entitlement grace period contract
  `[ENT-GRC-01] -> [PRD-§7]`
  > **Preconditions:** Phase 0 complete
  > **Target File:** `src/aetherlink/core/grace_period.py`
  > **Test File:** `tests/test_grace_period.py`
  > **Behavior:** TTL cache with `GRACE` → `LOCKED` transition on expiry.
  > States: `ELIGIBLE`, `GRACE`, `LOCKED`. Expiry must be deterministic and
  > testable via injected clock.
  > **Validation:** `uv run pytest tests/test_grace_period.py -vv`
  > **Evidence:** `locked == True` asserted after simulated TTL expiry.
  > **ARP Trigger:** Report actual vs expected state and the injected
  > timestamp used before any fix attempt.

- [ ] Implement environment dependency tracker
  `[ENV-DEP-01] -> [PRD-§5.10.1]`
  > **Preconditions:** None
  > **Target File:** `src/aetherlink/core/env_manager.py`
  > **Test File:** `tests/test_env_manager.py`
  > **Behavior:** Returns structured dict with `dep_count` (int) and
  > `disk_bytes` (int) for a given venv path. Uses `uv` subprocess. Mocked
  > in tests.
  > **Validation:** `uv run pytest tests/test_env_manager.py -vv`
  > **Evidence:** Both required fields present and correctly typed in
  > assertions.
  > **ARP Trigger:** Report which field is missing or has the wrong type
  > before any fix attempt.

### Phase 1 Exit Criteria
`[PLT-EXIT-01] -> [PRD-§4]`

```bash
uv run pytest tests/test_ui_shell.py
uv run pytest tests/test_xinput.py
uv run pytest tests/test_grace_period.py
uv run pytest tests/test_env_manager.py
uv run ruff check . && uv run pytest tests/ -x
```

---

## Phase 2 — Capture + Worker Integration

Goal: capture pipeline operational end-to-end via OpenCV plugin, workers
supervised, shared memory ring functional.

### Work Items

- [ ] Deliver OpenCV capture plugin contract
  `[CAP-OCV-01] -> [PRD-§5.4.1]`
  > **Preconditions:** `[IPC-SHM-01]`, `[ABI-FRZ-01]` complete
  > **Target File (Python):** `src/aetherlink/vision/cv_capture.py`
  > **Target File (Native):** `host/plugins/cv_capture.cpp`
  > **Test File:** `tests/test_cv_capture.py`
  > **Behavior:** Native/Python capture contract + shared memory mapping
  > **Command:** `uv run pytest tests/test_cv_capture.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** `get_mode_matrix()` typed list return
  > **ARP Trigger:** Report signature mismatch details

- [ ] Implement capability matrix filtering contract
  `[CAP-MAT-01] -> [PRD-§5.4.2]`
  > **Preconditions:** `[CAP-OCV-01]` complete
  > **Target Files:** `host/capability_matrix_filtering.cpp`,
  > `include/capability_matrix_filtering.h`
  > **Test File:** `tests/test_capability_matrix.cpp`
  > **Behavior:** Reject invalid capability schemas
  > **Command:** `g++ -std=c++20 tests/test_capability_matrix.cpp -I include/ && ./a.out`
  > **Validation:** Exit 0
  > **Evidence:** compile clean + assertions pass
  > **ARP Trigger:** Report exact g++ error before fix

- [ ] Implement worker supervisor
  `[WRK-SUP-01] -> [PRD-§5.9]`
  > **Preconditions:** `[IPC-FRZ-01]`, `[IPC-SHM-01]` complete
  > **Target Files:** `src/aetherlink/core/supervisor.py`,
  > `host/worker_supervisor.cpp`
  > **Test File:** `tests/test_supervisor.py`
  > **Behavior:** Spawn, heartbeat, restart with backoff (< 3s). States per
  > `[WRK-TAR-01]` in PRD §5.9. Python supervisor manages gRPC health channel.
  > C++ supervisor manages native process lifecycle.
  > **Validation:** `uv run pytest tests/test_supervisor.py -vv`
  > **Evidence:** Restart-within-threshold assertion passes with mocked
  > subprocess.
  > **ARP Trigger:** Report subprocess state and elapsed restart time on
  > heartbeat timeout before any fix attempt.

- [ ] Add performance HUD panel
  `[UI-HUD-01] -> [PRD-§6]`
  > **Preconditions:** `[UI-SHL-01]` complete
  > **Target File:** `src/aetherlink/ui/panels/performance_hud.py`
  > **Test File:** `tests/test_performance_hud.py`
  > **Behavior:** Widget showing FPS, latency, dropped frames, worker health.
  > Instantiates headlessly without crash. Default values asserted.
  > **Validation:** `uv run pytest tests/test_performance_hud.py -vv`
  > **Evidence:** Widget instantiation and default field assertions pass.
  > **ARP Trigger:** Report exact Qt error or missing widget attribute before
  > any fix attempt.

### Phase 2 Exit Criteria

```bash
uv run pytest tests/test_opencv_capture.py
uv run pytest tests/test_supervisor.py
uv run pytest tests/test_performance_hud.py
uv run ruff check . && uv run pytest tests/ -x
```

---

## Phase 3 — Environment + Online Resources

Goal: one-click environment bundle install, signed artifact verification,
resource browsing UI.

### Work Items

- [ ] Deliver environment bundle installer
  `[ENV-BUN-01] -> [PRD-§5.10.2]`
  > **Preconditions:** `[ENV-DEP-01]` complete
  > **Target File:** `src/aetherlink/core/bundle_installer.py`
  > **Test File:** `tests/test_bundle_installer.py`
  > **Behavior:** Extracts bundle, verifies SHA-256 + manifest, streams install
  > logs, supports CPU/CUDA variants. States per `[ENV-TAR-01]` in PRD §5.10.2.
  > **Validation:** `uv run pytest tests/test_bundle_installer.py -vv`
  > **Evidence:** All state transition assertions pass with mocked `uv sync`.
  > **ARP Trigger:** Report which state transition failed and the actual vs
  > expected state before any fix attempt.

- [ ] Implement signed artifact verifier
  `[RES-SIG-01] -> [PRD-§5.11.2]`
  > **Preconditions:** Phase 0 complete
  > **Target Files:** `src/aetherlink/core/security.py`,
  > `host/artifact_verifier.cpp`
  > **Test File:** `tests/test_security.py`
  > **Behavior:** SHA-256 + signature enforcement. Valid and tampered paths
  > both tested. `SecurityError` raised on failure.
  > **Validation:** `uv run pytest tests/test_security.py -vv`
  > **Evidence:** Valid pass and tampered-reject assertions both present.
  > **ARP Trigger:** Report which verification path failed and the actual
  > exception raised before any fix attempt.

- [ ] Add online resources browser panel
  `[UI-RES-01] -> [PRD-§5.11, §6]`
  > **Preconditions:** `[RES-SIG-01]`, `[UI-SHL-01]` complete
  > **Target File:** `src/aetherlink/ui/panels/online_resources.py`
  > **Test File:** `tests/test_online_resources.py`
  > **Behavior:** Catalog modal with one-click install and streamed logs.
  > Rendered item count matches catalog mock.
  > **Validation:** `uv run pytest tests/test_online_resources.py -vv`
  > **Evidence:** Item count assertion passes with mocked catalog.
  > **ARP Trigger:** Report Qt render error or catalog mock mismatch before
  > any fix attempt.

### Phase 3 Exit Criteria

```bash
uv run pytest tests/test_bundle_installer.py
uv run pytest tests/test_security.py
uv run pytest tests/test_online_resources.py
uv run ruff check . && uv run pytest tests/ -x
```

---

## Phase 4 — Entitlements + Admin

Goal: premium plugin gating enforced end-to-end, admin dashboard operational.

### Work Items

- [ ] Implement entitlement validation contract
  `[ENT-VAL-01] -> [PRD-§7, §5.1.3]`
  > **Preconditions:** Phase 3 complete
  > **Target File:** `src/aetherlink/core/entitlements.py`
  > **Test File:** `tests/test_entitlement_check.py`
  > **Behavior:** JWT/cache checks + offline grace transitions per
  > `[ENT-TAR-01]` state machine in PRD §5.1.5. All 7 state transitions tested.
  > **Validation:** `uv run pytest tests/test_entitlement_check.py -vv`
  > **Evidence:** All state transitions logged and asserted.
  > **ARP Trigger:** Report which state transition produced the wrong result
  > and the token/cache state at time of failure before any fix attempt.

- [ ] Enforce premium plugin gate in loader
  `[ENT-GAT-01] -> [PRD-§5.1.3]`
  > **Preconditions:** `[ENT-VAL-01]`, `[ABI-LDR-01]` complete
  > **Target File:** `host/plugin_loader.cpp`
  > **Test File:** `tests/test_premium_gate.py`
  > **Behavior:** `PluginLoader` blocks any premium DLL load when entitlement
  > invalid. Python test mocks the entitlement check and asserts
  > `PluginLoadError` is raised for the locked path.
  > **Validation:** `uv run pytest tests/test_premium_gate.py -vv`
  > **Evidence:** Blocked-load assertion passes; no DLL loaded without token.
  > **ARP Trigger:** Report which entitlement state allowed a load that should
  > have been blocked before any fix attempt.

- [ ] Deliver admin API contract
  `[PLT-ADM-01] -> [PRD-§5.12]`
  > **Preconditions:** `[ENT-VAL-01]` complete
  > **Target File:** `src/aetherlink/core/admin_api.py`
  > **Test File:** `tests/test_admin_api.py`
  > **Behavior:** User management, entitlement assignment, session revocation,
  > audit log. All endpoint response schemas validated.
  > **Validation:** `uv run pytest tests/test_admin_api.py -vv`
  > **Evidence:** Schema key assertions pass for all endpoints.
  > **ARP Trigger:** Report which endpoint returned the wrong schema and the
  > actual vs expected keys before any fix attempt.

- [ ] Admin dashboard UI panel
  `[UI-ADM-01] -> [PRD-§5.12]`
  > **Preconditions:** `[PLT-ADM-01]`, `[UI-SHL-01]` complete
  > **Target File:** `src/aetherlink/ui/panels/admin_dashboard.py`
  > **Test File:** `tests/test_admin_dashboard.py`
  > **Behavior:** Modal launches with mocked entitlement data. Widget
  > instantiation assertions pass headlessly.
  > **Validation:** `uv run pytest tests/test_admin_dashboard.py -vv`
  > **Evidence:** Widget instantiation and mocked data assertions pass.
  > **ARP Trigger:** Report exact Qt error or missing widget attribute before
  > any fix attempt.

### Phase 4 Exit Criteria

```bash
uv run pytest tests/test_entitlement_check.py
uv run pytest tests/test_premium_gate.py
uv run pytest tests/test_admin_api.py
uv run pytest tests/test_admin_dashboard.py
uv run ruff check . && uv run pytest tests/ -x
```

---

## Traceability Index

| PRD Section | IDs |
| --- | --- |
| §4.1 Microkernel | `ABI-LDR-01`, `ABI-SVC-01` |
| §4.4 Frozen Contracts | `ABI-FRZ-01`, `IPC-FRZ-01`, `IPC-SHM-01` |
| §5.1.2 Plugin Contract | `ABI-FRZ-01`, `ABI-PY-01` |
| §5.1.3 Premium Gating | `ENT-GAT-01`, `ENT-VAL-01` |
| §5.1.4 Plugin Loading | `ABI-LDR-01` |
| §5.2 Controller Adapter | `ABI-IO-01` |
| §5.4 Capture System | `CAP-OCV-01` |
| §5.6 Input Devices | `ABI-IO-01` |
| §5.9 Python Workers | `IPC-FRZ-01`, `IPC-SHM-01`, `WRK-SUP-01` |
| §5.10 uv Environments | `ENV-DEP-01`, `ENV-BUN-01` |
| §5.11 Online Resources | `RES-SIG-01`, `UI-RES-01` |
| §5.12 Admin Dashboard | `PLT-ADM-01`, `UI-ADM-01` |
| §6 UX | `UI-SHL-01`, `UI-HUD-01` |
| §7 Entitlements | `ENT-VAL-01`, `ENT-GAT-01`, `ENT-GRC-01` |

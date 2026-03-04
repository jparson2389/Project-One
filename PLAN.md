# Implementation Plan — Traceability + ARP

This plan follows `PRD-PLAN-Transformation-Proposal.md` with deterministic
Traceability IDs and Atomic Recovery Protocol (ARP) requirements.

---

## Traceability ID Convention

Every work item must include:

`[DOMAIN-TYPE-NN] -> [PRD-§X.Y]`

Domain prefixes:
- `ABI` Plugin ABI / contract boundaries
- `CAP` Capture system
- `ENT` Entitlements + premium gating
- `ENV` Environment management
- `IPC` gRPC + shared memory
- `PLT` Platform, auth, CI
- `RES` Online Resources + CDN
- `UI` UX shell + panels
- `WRK` Worker supervisor

---

## Atomic Recovery Protocol (ARP)

If any validation command exits non-zero:
1. CAPTURE: `git diff > _recovery/failed_state_<timestamp>.patch`
2. ANALYZE: `uv run ruff check <failing_file>` and
   `uv run pytest <failing_test> -vv`
3. REPORT: "Validation failed because: <reason>. Affected file: <path>."
4. FIX: one minimal fix attempt
5. REVERT: if second validation fails, restore and report BLOCKED

---

## Work Item Template

- [ ] `<Title>`
  `[DOMAIN-TYPE-NN] -> [PRD-§X.Y]`
  > **Preconditions:** <what must already exist>
  > **Target Files:** `path/to/file`
  > **Test File:** `tests/test_file.py`
  > **Behavior:** <what it does>
  > **Command:** `uv run ...`
  > **Validation:** exit 0 required
  > **Evidence:** `logs/...` or file existence
  > **ARP Trigger:** if Command exits non-zero, execute ARP before retry

---

## Phase 0 — Core Architecture & Boundaries

### Work Items

- [ ] Resolve placeholder files for remote-play and GPU renderer
  `[ABI-DEV-01] -> [PRD-§5.4, §5.7]`
  > **Preconditions:** None
  > **Target Files:** `src/aetherlink/plugins/capture/_stubs/test_plugin_stubs.py`
  > **Test File:** `tests/test_no_placeholders.py`
  > **Behavior:** No placeholder files masquerade as completed logic in `_stubs/`
  > **Command:** `uv run pytest tests/test_no_placeholders.py -vv`
  > **Validation:** Exit 0, 0 failures
  > **Evidence:** Clean `ls src/aetherlink/plugins/capture/_stubs/`
  > **ARP Trigger:** On failure, capture diff, report violating stubs, revert

- [ ] Freeze plugin ABI
  `[ABI-FRZ-01] -> [PRD-§5.1.2, §4.4]`
  > **Preconditions:** None
  > **Target File:** `src/aetherlink/plugins/include/plugin_system.hpp`
  > **Test File:** `tests/test_plugin_abi.cpp`
  > **Behavior:** Strict C-ABI boundaries and lifecycle contracts
  > **Command:** `g++ -std=c++20 -c tests/test_plugin_abi.cpp -I src/aetherlink/plugins/include/`
  > **Validation:** Exit 0
  > **Evidence:** `docs/breaking-changes/abi.md` entry created
  > **ARP Trigger:** On compile failure, report exact compiler error first

- [ ] Freeze gRPC proto
  `[IPC-FRZ-01] -> [PRD-§5.9, §4.4]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target File:** `src/aetherlink/proto/capture.proto`
  > **Output Files:** `src/aetherlink/proto/capture_pb2.py`, `capture_pb2_grpc.py`
  > **Test File:** `tests/test_capture_proto.py`
  > **Behavior:** Control-plane gRPC services for worker management
  > **Command:** `uv run python -m grpc_tools.protoc -I src/aetherlink/proto/ --python_out=src/aetherlink/proto/ --grpc_python_out=src/aetherlink/proto/ src/aetherlink/proto/capture.proto && uv run pytest tests/test_capture_proto.py -vv`
  > **Validation:** Exit 0, files generated, tests pass
  > **Evidence:** `src/aetherlink/proto/capture_pb2.py` exists; proto change log entry
  > **ARP Trigger:** Report exact protoc/pytest failure before fix

- [ ] Define shared memory layout contract
  `[IPC-SHM-01] -> [PRD-§5.9, §4.4]`
  > **Preconditions:** `[IPC-FRZ-01]` complete
  > **Target File:** `src/aetherlink/core/shared_memory_layout.py`
  > **Test File:** `tests/test_shared_memory_layout.py`
  > **Behavior:** Deterministic ring buffer layout
  > **Command:** `uv run pytest tests/test_shared_memory_layout.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** `docs/breaking-changes/shmem.md` entry created
  > **ARP Trigger:** Report failing offset assertion before fix

- [ ] Implement remote-play integration stub
  `[CAP-RMP-01] -> [PRD-§5.7]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target Files:** `src/aetherlink/core/remote_play.py`
  > **Test File:** `tests/test_remote_play.py`
  > **Behavior:** Importable module with defined interfaces
  > **Command:** `uv run pytest tests/test_remote_play.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** `uv run python -c "import aetherlink.core.remote_play"` exits 0
  > **ARP Trigger:** Report ImportError dependency before fix

- [ ] Complete GPU renderer plugin
  `[UI-GPU-01] -> [PRD-§5.5]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target Files:** `src/aetherlink/plugins/capture/gpu_renderer.py`
  > **Test File:** `tests/test_gpu_renderer_plugin.py`
  > **Behavior:** Replace placeholder, no pipeline crash
  > **Command:** `uv run pytest tests/test_gpu_renderer_plugin.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** No `_stub` markers remain
  > **ARP Trigger:** Capture traceback before fix attempt

- [ ] Add dependency tracking for environment management
  `[ENV-DEP-01] -> [PRD-§5.10.1]`
  > **Preconditions:** None
  > **Target Files:** `src/aetherlink/core/env_manager.py`
  > **Test File:** `tests/test_dependency_tracking.py`
  > **Behavior:** Emit structured dependency count and disk usage
  > **Command:** `uv run pytest tests/test_dependency_tracking.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** Dict contains `dep_count` and `disk_bytes`
  > **ARP Trigger:** Report missing/wrong field before fix

- [ ] Integrate admin dashboard UI elements
  `[UI-ADM-01] -> [PRD-§5.12]`
  > **Preconditions:** `[ENT-VAL-01]` in Phase 4 reviewed
  > **Target Files:** `src/aetherlink/ui/panels/admin_dashboard.py`
  > **Test File:** `tests/test_admin_dashboard.py`
  > **Behavior:** Modal launches with mocked entitlement data
  > **Command:** `uv run pytest tests/test_admin_dashboard.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** Widget instantiation assertions pass
  > **ARP Trigger:** Capture Qt stderr before fix

### Phase 0 Exit Criteria
`[PLT-EXIT-00] -> [PRD-§4]`

```bash
uv run pytest tests/test_no_placeholders.py
g++ -std=c++20 -c tests/test_plugin_abi.cpp -I src/aetherlink/plugins/include/
uv run pytest tests/test_capture_proto.py
uv run pytest tests/test_shared_memory_layout.py
uv run ruff check . && uv run pytest tests/ -x
```

---

## Phase 1 — UI Shell & Core Framework

### Work Items

- [ ] Deliver basic PySide6 Qt shell
  `[UI-SHL-01] -> [PRD-§6]`
  > **Preconditions:** Phase 0 exit criteria passed
  > **Target Files:** `src/aetherlink/main.py`, `src/aetherlink/ui/main_window.py`
  > **Test File:** `tests/test_ui_shell.py`
  > **Behavior:** `QApplication` and `MainWindow` initialize cleanly
  > **Command:** `uv run pytest tests/test_ui_shell.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** `uv run python -c "from aetherlink.ui.main_window import MainWindow"` exits 0
  > **ARP Trigger:** Report missing Qt bindings before fix

- [ ] Sweep and isolate plugin placeholders
  `[ABI-DEV-02] -> [PRD-§5.1]`
  > **Preconditions:** `[ABI-DEV-01]` complete
  > **Target Files:** `src/aetherlink/plugins/capture/_stubs/*`
  > **Behavior:** Stubs implemented or removed; no dangling schemas
  > **Command:** `uv run pytest tests/test_no_placeholders.py -vv`
  > **Validation:** Exit 0; stubs directory empty/absent
  > **Evidence:** `ls src/aetherlink/plugins/capture/_stubs/` empty
  > **ARP Trigger:** List remaining files and reason before fix

- [ ] Isolate or sequence offline grace logic
  `[ENT-GRC-01] -> [PRD-§7]`
  > **Preconditions:** Phase 0 complete
  > **Target Files:** `src/aetherlink/core/grace_period.py`
  > **Test File:** `tests/test_grace_period.py`
  > **Behavior:** Formal TTL expiry behavior or explicit sequencing to Phase 4
  > **Command:** `uv run pytest tests/test_grace_period.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** `entitlement.locked == True` after TTL expiry
  > **ARP Trigger:** Report actual vs expected expiry time

- [ ] Implement remote-play integrations
  `[CAP-RMP-02] -> [PRD-§5.7]`
  > **Preconditions:** `[CAP-RMP-01]` complete
  > **Target Files:** `src/aetherlink/core/remote_play.py`
  > **Test File:** `tests/test_remote_play.py`
  > **Behavior:** Concrete interfaces linked into core pipeline
  > **Command:** `uv run pytest tests/test_remote_play.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** Module importable without errors
  > **ARP Trigger:** Report missing interface method before fix

- [ ] Complete scripting and inference engine plugins
  `[WRK-INF-01] -> [PRD-§5.8]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target Files:** `src/aetherlink/plugins/inference_engine.py`
  > **Test File:** `tests/test_inference_engine.py`
  > **Behavior:** Plugin abstraction + registration behavior
  > **Command:** `uv run pytest tests/test_inference_engine.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** No `PluginLoadError` on registration
  > **ARP Trigger:** Report missing contract method

- [ ] Implement baseline input and output plugin contracts
  `[ABI-IO-01] -> [PRD-§5.2, §5.6]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target Files (Python):** `src/aetherlink/input/xinput.py`,
  > `src/aetherlink/output/vigem.py`
  > **Target Files (Native):** `host/plugins/xinput_provider.cpp`,
  > `host/plugins/vigem_output.cpp`
  > **Test File:** `tests/test_io_plugins.py`
  > **Behavior:** IO interfaces and native ABI exports
  > **Command:** `uv run python -c "import aetherlink.input.xinput; import aetherlink.output.vigem" && uv run pytest tests/test_io_plugins.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** both Python interfaces importable
  > **ARP Trigger:** Report module path failure before fix

- [ ] Test and validate subsystem interactions (split)
  `[ABI-INT-01] -> [PRD-§5.2, §5.4, §5.9]`
  > **Behavior:** Split into capture/worker, IO pipeline, entitlement/loader tests

  - [ ] Capture <-> Worker integration test
    `[CAP-INT-01] -> [PRD-§5.4, §5.9]`
    > **Command:** `uv run pytest tests/integration/test_capture_worker.py -vv`
    > **Evidence:** frame handoff assertion passes

  - [ ] Input <-> Output pipeline integration test
    `[ABI-INT-02] -> [PRD-§5.2]`
    > **Command:** `uv run pytest tests/integration/test_io_pipeline.py -vv`
    > **Evidence:** latency <= 5ms assertion

  - [ ] Entitlement <-> Plugin loader integration test
    `[ENT-INT-01] -> [PRD-§5.1.3, §7]`
    > **Command:** `uv run pytest tests/integration/test_entitlement_loader.py -vv`
    > **Evidence:** blocked load logged with no entitlement

### Phase 1 Exit Criteria
`[PLT-EXIT-01] -> [PRD-§4]`

```bash
uv run pytest tests/test_ui_shell.py
uv run pytest tests/test_no_placeholders.py
uv run python -c "import aetherlink.input.xinput; import aetherlink.output.vigem"
uv run ruff check . && uv run pytest tests/ -x
```

---

## Phase 2 — Capture + Worker Integration

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

- [ ] Implement worker supervisor + IPC
  `[WRK-SUP-01] -> [PRD-§5.9]`
  > **Preconditions:** `[IPC-FRZ-01]`, `[IPC-SHM-01]` complete
  > **Target Files:** `host/worker_supervisor.cpp`, `src/aetherlink/core/supervisor.py`
  > **Test File:** `tests/test_supervisor.py`
  > **Behavior:** Spawn, heartbeat, restart with backoff (< 3s)
  > **Command:** `uv run pytest tests/test_supervisor.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** restart completed within threshold
  > **ARP Trigger:** Report subprocess state on heartbeat timeout

- [ ] Add performance HUD panel
  `[UI-HUD-01] -> [PRD-§6]`
  > **Preconditions:** `[UI-SHL-01]` complete
  > **Target File:** `src/aetherlink/ui/panels/performance_hud.py`
  > **Test File:** `tests/test_performance_hud.py`
  > **Behavior:** Real-time FPS, latency, and resource metrics
  > **Command:** `uv run pytest tests/test_performance_hud.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** widget render and default assertions pass
  > **ARP Trigger:** Report Qt error on instantiation failure

### Phase 2 Exit Criteria
`[PLT-EXIT-02] -> [PRD-§4]`

```bash
uv run pytest tests/test_cv_capture.py
g++ -std=c++20 tests/test_capability_matrix.cpp -I include/ && ./a.out
uv run pytest tests/test_supervisor.py
uv run ruff check . && uv run pytest tests/ -x
```

---

## Phase 3 — Environment + Resource System

### Work Items

- [ ] Implement uv environment management contract
  `[ENV-MGR-01] -> [PRD-§5.10.1]`
  > **Preconditions:** `[ENV-DEP-01]` complete
  > **Target File:** `src/aetherlink/core/env_manager.py`
  > **Test File:** `tests/test_env_manager.py`
  > **Behavior:** Isolated `uv` environment lifecycle metadata
  > **Command:** `uv run pytest tests/test_env_manager.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** mocked `uv venv` invocation matches expected args
  > **ARP Trigger:** Report actual call args before fix

- [ ] Deliver environment bundle installer contract
  `[ENV-BUN-01] -> [PRD-§5.10.2]`
  > **Preconditions:** `[ENV-MGR-01]` complete
  > **Target File:** `src/aetherlink/core/bundle_installer.py`
  > **Test File:** `tests/test_bundle_installer.py`
  > **Behavior:** Extract, verify manifest, stream logs, support variants
  > **Command:** `uv run pytest tests/test_bundle_installer.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** manifest fields validated in tests
  > **ARP Trigger:** Report missing manifest field

- [ ] Implement signed artifact verification contract
  `[RES-SIG-01] -> [PRD-§5.11.2]`
  > **Preconditions:** Phase 0 complete
  > **Target Files:** `host/artifact_verifier.cpp`, `src/aetherlink/core/security.py`
  > **Test File:** `tests/test_security.py`
  > **Behavior:** SHA-256 + signature enforcement
  > **Command:** `uv run pytest tests/test_security.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** valid and invalid paths asserted
  > **ARP Trigger:** Report actual exception vs expected

- [ ] Add resource browsing UI panel
  `[UI-RES-01] -> [PRD-§5.11, §6]`
  > **Preconditions:** `[RES-SIG-01]`, `[UI-SHL-01]` complete
  > **Target File:** `src/aetherlink/ui/panels/online_resources.py`
  > **Test File:** `tests/test_online_resources.py`
  > **Behavior:** Catalog modal with one-click install and streamed logs
  > **Command:** `uv run pytest tests/test_online_resources.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** rendered item count matches catalog mock
  > **ARP Trigger:** Capture Qt render error before fix

### Phase 3 Exit Criteria
`[PLT-EXIT-03] -> [PRD-§4]`

```bash
uv run pytest tests/test_env_manager.py
uv run pytest tests/test_bundle_installer.py
uv run pytest tests/test_security.py
uv run ruff check . && uv run pytest tests/ -x
```

---

## Phase 4 — Entitlements + Admin

### Work Items

- [ ] Implement entitlement validation contract
  `[ENT-VAL-01] -> [PRD-§7, §5.1.3]`
  > **Preconditions:** Phase 3 complete
  > **Target File:** `src/aetherlink/core/entitlements.py`
  > **Target File (Native):** `host/entitlement_check.cpp`
  > **Test File:** `tests/test_entitlement_check.py`
  > **Behavior:** JWT/cache checks + offline grace transitions
  > **Command:** `uv run pytest tests/test_entitlement_check.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** all state transitions logged
  > **ARP Trigger:** Report actual vs expected state transition

- [ ] Implement premium plugin gating contract
  `[ENT-GAT-01] -> [PRD-§5.1.3]`
  > **Preconditions:** `[ENT-VAL-01]`, `[ABI-FRZ-01]` complete
  > **Target Files (Native):** `host/plugin_loader.cpp`
  > **Test File:** `tests/test_plugin_loader.cpp`
  > **Behavior:** Block premium DLL mapping without entitlement
  > **Command:** `g++ -std=c++20 tests/test_plugin_loader.cpp && ./a.out`
  > **Validation:** Exit 0
  > **Evidence:** blocked-load log emitted
  > **ARP Trigger:** Report which gate was bypassed on failure

- [ ] Deliver admin APIs contract
  `[PLT-ADM-01] -> [PRD-§5.12]`
  > **Preconditions:** `[ENT-VAL-01]` complete
  > **Target File:** `src/aetherlink/core/admin_api.py`
  > **Test File:** `tests/test_admin_api.py`
  > **Behavior:** User management, entitlement assignment, revocation, audit
  > **Command:** `uv run pytest tests/test_admin_api.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** endpoint response schemas match
  > **ARP Trigger:** Report schema key mismatch details

- [ ] Implement offline grace logic contract
  `[ENT-GRC-02] -> [PRD-§7]`
  > **Preconditions:** `[ENT-VAL-01]`, `[ENT-GRC-01]` complete
  > **Target File:** `src/aetherlink/core/grace_period.py`
  > **Test File:** `tests/test_grace_period_logic.py`
  > **Behavior:** TTL cache with premium lock on expiry
  > **Command:** `uv run pytest tests/test_grace_period_logic.py -vv`
  > **Validation:** Exit 0
  > **Evidence:** lock asserted after simulated expiry
  > **ARP Trigger:** Report expected vs actual expiry timestamp

### Phase 4 Exit Criteria
`[PLT-EXIT-04] -> [PRD-§4, §7]`

```bash
uv run pytest tests/test_entitlement_check.py
g++ -std=c++20 tests/test_plugin_loader.cpp && ./a.out
uv run pytest tests/test_grace_period_logic.py
uv run ruff check . && uv run pytest tests/ --tb=short
```

---

## Traceability Index

| PRD Section | Traceability IDs |
| --- | --- |
| §4 (Architectural Principles) | `ABI-FRZ-01`, `IPC-FRZ-01`, `IPC-SHM-01`, `PLT-BND-01`, `PLT-EXIT-*` |
| §5.1 (Plugin System) | `ABI-FRZ-01`, `ABI-DEV-01/02`, `ABI-IO-01`, `ENT-GAT-01` |
| §5.2 (Controller Adapter) | `ABI-IO-01`, `ABI-INT-02` |
| §5.4 (Capture System) | `CAP-OCV-01`, `CAP-MAT-01`, `CAP-RMP-01/02`, `UI-GPU-01`, `CAP-INT-01` |
| §5.5 (Display/Render) | `UI-GPU-01` |
| §5.6 (Input Devices) | `ABI-IO-01` |
| §5.7 (Remote-Play) | `CAP-RMP-01/02` |
| §5.8 (Scripting/Inference) | `WRK-INF-01` |
| §5.9 (Python Workers) | `IPC-FRZ-01`, `IPC-SHM-01`, `WRK-SUP-01`, `WRK-TAR-01` |
| §5.10 (uv Environments) | `ENV-DEP-01`, `ENV-MGR-01`, `ENV-BUN-01`, `ENV-TAR-01` |
| §5.11 (Online Resources) | `RES-SIG-01`, `UI-RES-01` |
| §5.12 (Admin Dashboard) | `UI-ADM-01`, `PLT-ADM-01` |
| §6 (UX Requirements) | `UI-SHL-01`, `UI-HUD-01`, `UI-RES-01`, `UI-PER-01` |
| §7 (Entitlements) | `ENT-VAL-01`, `ENT-GAT-01`, `ENT-GRC-01/02`, `ENT-TAR-01`, `ENT-INT-01` |
| §9 (Success Metrics) | `PLT-MET-01` |

# PRD + PLAN Transformation Proposal
**Based on:** `ai-prd-transformation.md`
**Enhancements:** Gemini Traceability IDs + Atomic Recovery Protocol
**Date:** 2026-03-04

---

## Traceability ID Schema

Every item in this proposal uses a structured ID that links PLAN tasks back to PRD sections.
Format: `[DOMAIN-TYPE-NN] -> [PRD-§X.Y]`

| Domain Prefix | Meaning |
|---|---|
| `ABI` | Plugin ABI / contract boundaries |
| `CAP` | Capture system |
| `ENT` | Entitlements + premium gating |
| `ENV` | Environment management |
| `IPC` | gRPC + shared memory |
| `PLT` | Platform, auth, CI |
| `RES` | Online Resources + CDN |
| `UI` | UX Shell + panels |
| `WRK` | Worker supervisor |

---

## Atomic Recovery Protocol (ARP)

Any agent executing items in this plan MUST follow this protocol on validation failure:

```
STEP 1 — CAPTURE
  Save current diff: git diff > _recovery/failed_state_<timestamp>.patch

STEP 2 — ANALYZE
  Run: uv run ruff check <failing_file>
  Run: uv run pytest <failing_test> -vv
  Do NOT attempt a fix yet.

STEP 3 — REPORT
  State EXACTLY why the validation command failed before writing any code.
  Format: "Validation failed because: <reason>. Affected file: <path>."

STEP 4 — FIX (one attempt)
  Apply the minimal fix. Re-run the validation command.

STEP 5 — REVERT (if fix fails)
  If the fix fails a second time:
    git checkout -- <affected_files>
  Restore from: _recovery/failed_state_<timestamp>.patch
  Report status as BLOCKED with the exact error.
  Do NOT attempt a third fix autonomously.
```

> This protocol applies to every `Validation:` command in every PLAN item below.

---

## Part 1 — PRD.md Changes

### 1.1 Add G3 "Source of Truth" Block `[PLT-G3-01] -> [PRD-§1]`

Insert after the Executive Summary. This is the agent's cognitive anchor — it must appear
before any other section so it is consumed first in every context window.

```markdown
## G3 Framework — Cognitive Anchor

### Guidelines (Project Context + Intent)
- **Core thesis:** Microkernel host where everything is a plugin. No exceptions.
- **Platform:** Windows only (v1). No cross-platform abstractions.
- **Tech stack:** C++20 (native plugins), Python 3.12 (workers + UI), PySide6 6.9.x (shell).
- **IPC:** gRPC control plane + shared memory data plane. No alternatives.
- **Monetization:** Tiered entitlements. Premium plugins ship locked, not absent.
- **Priority order when requirements conflict:**
  Host Stability > Security/Signing > Feature Completeness > Performance > UX Polish

### Guidance (Interpretive Logic)
- When a PRD section is ambiguous, default to the most restrictive interpretation.
- "Contract" items (ABI, proto, shared memory layout) are frozen after Phase 0.
  Any agent that modifies a frozen contract MUST log a breaking-change entry.
- TDD is not optional. Tests are written first, executed to prove failure,
  then implementation is written, then tests are re-executed to prove passage.
- File paths in PLAN are canonical. Do not rename or relocate without a
  traceability update.

### Guardrails (Hard Boundaries + Automated Gates)
- NEVER load a premium plugin DLL without a valid entitlement token.
- NEVER execute an unsigned artifact.
- NEVER modify `plugin_system.hpp` without a breaking-change log entry.
- NEVER bypass gRPC for worker-to-host communication.
- NEVER write to `src/plugins/*` — use `src/aetherlink/plugins/*`.
- ASK FIRST: changes to `capture.proto`, `shared_memory_layout.py`,
  billing/entitlement state machine semantics, auth provider selection.
- ALWAYS run `uv run ruff check && uv run pytest` before marking an item done.
- ALWAYS use Loguru for logging — no print statements.
- ALWAYS use Google-format docstrings on all public Python functions.
- ALWAYS include type hints on all Python function signatures.
```

---

### 1.2 Replace §3 Personas with Role-Based Behavioral Models `[UI-PER-01] -> [PRD-§3]`

Current personas are descriptive archetypes. Replace with access-scoped behavioral models
that an agent can use to constrain UI logic and entitlement rules.

```markdown
## 3) Role-Based Behavioral Models

| Role | Access Scope | Entitlement Level | Key Behaviors |
|---|---|---|---|
| **Power Gamer** | Profile CRUD, mapping, fast-switch | Free/Pro | No admin, no billing, no env management |
| **Vision/ML Tinkerer** | Env create/delete, resource install, capture config | Pro/Vision | No billing admin, no user management |
| **Accessibility Modder** | Scripting VM, calibration tooling, automation primitives | Pro | No capture premium features unless entitled |
| **Admin/Operator** | Full entitlement + user management, audit log | Enterprise | Can revoke sessions, assign tiers, view all logs |
```

---

### 1.3 Add "DO NOT CHANGE" Protocol `[ABI-FRZ-01] -> [PRD-§4]`

New subsection §4.4. Prevents the improvement paradox on frozen contracts.

```markdown
### 4.4 Frozen Contracts — DO NOT CHANGE

The following are frozen after Phase 0 completion. No agent may modify these
without an explicit breaking-change log entry and human sign-off:

| File | Frozen After | Breaking Change Log Path |
|---|---|---|
| `src/aetherlink/plugins/include/plugin_system.hpp` | Phase 0 | `docs/breaking-changes/abi.md` |
| `src/aetherlink/proto/capture.proto` | Phase 0 | `docs/breaking-changes/proto.md` |
| `src/aetherlink/core/shared_memory_layout.py` | Phase 0 | `docs/breaking-changes/shmem.md` |
| `src/aetherlink/core/entitlements.py` (state machine) | Phase 4 | `docs/breaking-changes/entitlements.md` |

Agents that detect a required change to a frozen file MUST:
1. Stop execution.
2. Report: "FROZEN CONTRACT MODIFICATION REQUIRED: <file> — <reason>."
3. Await human instruction before proceeding.
```

---

### 1.4 Add "Never / Ask First / Always" Boundary Section `[PLT-BND-01] -> [PRD-§4]`

New subsection §4.5.

```markdown
### 4.5 Agent Boundary Rules

**NEVER:**
- Load premium plugin DLLs without a valid entitlement token
- Execute unsigned artifacts (plugins, environment bundles, model packages)
- Write to `src/plugins/*` (use `src/aetherlink/plugins/*`)
- Bypass the gRPC control plane for worker-to-host communication
- Commit secrets, API keys, or tokens
- Use `print()` — use `loguru.logger` instead

**ASK FIRST:**
- Any modification to a frozen contract (see §4.4)
- Changes to entitlement state machine semantics
- Auth provider selection or changes
- Database schema changes
- Billing or pricing logic changes
- Remote-play v1 vs v1.1 scoping decisions

**ALWAYS:**
- Run `uv run ruff check && uv run pytest` before marking a work item done
- Write tests first (TDD) — prove failure before writing implementation
- Use Google-format docstrings on all public Python functions
- Use type hints on all Python function signatures
- Log breaking-change entries before modifying frozen contracts
- Document new gRPC endpoints in `docs/proto/`
```

---

### 1.5 Add TAR State Machines for Critical Flows `[ENT-TAR-01] -> [PRD-§5.1.3]`

New subsection §5.1.5. State machines the agent can reference when implementing
entitlement, worker, and bundle flows.

```markdown
### 5.1.5 Critical State Machines (TAR Format)

#### Entitlement / Premium Plugin Gating
`[ENT-TAR-01] -> [PRD-§5.1.3, §7]`

| Trigger | Condition | Action | Result State |
|---|---|---|---|
| `Host::LoadPlugin(plugin_id)` called | Plugin is NOT premium | Load normally | `LOADED` |
| `Host::LoadPlugin(plugin_id)` called | Plugin is premium, entitlement valid | Load plugin | `LOADED` |
| `Host::LoadPlugin(plugin_id)` called | Plugin is premium, entitlement invalid | Block load, show purchase CTA | `LOCKED` |
| Purchase completed | Entitlement token received | Refresh entitlement cache | `ELIGIBLE` |
| Entitlement refresh | Token valid | Enable plugin without reinstall | `LOADED` |
| TTL expires (offline) | Grace period active | Warn user, maintain access | `GRACE` |
| TTL expires (offline) | Grace period expired | Lock premium features | `LOCKED` |

#### Python Worker Lifecycle
`[WRK-TAR-01] -> [PRD-§5.9]`

| Trigger | Condition | Action | Result State |
|---|---|---|---|
| Worker start requested | Env valid, supervisor running | Spawn subprocess, start heartbeat | `STARTING` |
| Heartbeat received | Within timeout | Update health state | `RUNNING` |
| Heartbeat missed | Within retry window | Increment miss counter | `DEGRADED` |
| Heartbeat missed | Retry window exceeded | Kill + restart with backoff | `RECOVERING` |
| Worker crash detected | Any | Log crash, trigger restart | `RECOVERING` |
| Restart succeeds | — | Resume heartbeat monitoring | `RUNNING` |
| Restart fails 3x | — | Mark worker FAILED, alert UI | `FAILED` |

#### Environment Bundle Install
`[ENV-TAR-01] -> [PRD-§5.10.2]`

| Trigger | Condition | Action | Result State |
|---|---|---|---|
| Install initiated | SHA-256 valid, signature valid | Extract bundle, stream logs | `INSTALLING` |
| Install initiated | SHA-256 mismatch | Reject, show error | `FAILED` |
| `uv sync` completes | Exit 0 | Validate imports | `VERIFYING` |
| Validation passes | All imports resolve | Mark env ready | `READY` |
| Validation fails | Import error | Show failed deps, offer repair | `FAILED` |
```

---

### 1.6 Upgrade §9 Success Metrics to Machine-Verifiable `[PLT-MET-01] -> [PRD-§9]`

```markdown
## 9) Success Metrics (Machine-Verifiable)

| Metric | Target | Verification Method | Evidence Artifact |
|---|---|---|---|
| Install → working baseline mapping | Median ≤ 5 min on clean Win11 VM | Automated e2e test script | `logs/onboarding_timing.json` |
| Environment bundle install success rate | ≥ 95% over 100 simulated installs | `uv run pytest tests/test_bundle_installer.py --count=100` | `logs/bundle_install_report.json` |
| Host survivability on worker crash | ≥ 99.9% (host stays running) | `uv run pytest tests/stress/test_worker_crash_loop.py -n 1000` | `logs/survivability_report.json` |
| Capture stability at 60 FPS baseline | ≥ 95% sessions without sustained drops | `uv run pytest tests/integration/test_capture_stability.py` | `logs/capture_stability.json` |
| Premium plugin blocked without entitlement | 100% block rate | `uv run pytest tests/test_plugin_loader.cpp` | `logs/entitlement_gate_report.json` |
| Unsigned artifact execution | 0 occurrences | `uv run pytest tests/test_security.py` | `logs/security_audit.json` |
```

---

## Part 2 — PLAN.md Changes

### 2.1 Traceability ID Convention for All Work Items

Every work item gets a Traceability ID header in this format:

```
`[DOMAIN-TYPE-NN] -> [PRD-§X.Y]`
```

This allows querying: *"Show me all PLAN items related to PRD §5.1.3"* and getting
a deterministic, exhaustive list.

---

### 2.2 Phase Exit Criteria (All Phases)

Each phase ends with a machine-checkable exit gate. The agent MUST NOT proceed to
the next phase until all exit criteria pass.

---

### 2.3 Enhanced Work Item Template

Every item follows this structure:

```markdown
- [ ] <Title>
  `[DOMAIN-TYPE-NN] -> [PRD-§X.Y]`
  > **Preconditions:** <what must already exist>
  > **Target Files:** `path/to/file`
  > **Test File:** `tests/test_file.py`
  > **Behavior:** <what it does>
  > **Command:** `uv run ...`
  > **Validation:** exit 0 required
  > **Evidence:** `logs/...` or file existence
  > **ARP Trigger:** if Command exits non-zero, execute ARP before retry
```

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
  > **ARP Trigger:** On failure, capture diff, report which stubs are violating, revert

- [ ] Freeze plugin ABI
  `[ABI-FRZ-01] -> [PRD-§5.1.2, §4.4]`
  > **Preconditions:** None
  > **Target File:** `src/aetherlink/plugins/include/plugin_system.hpp`
  > **Test File:** `tests/test_plugin_abi.cpp`
  > **Behavior:** Strict C-ABI boundaries. Structs for PluginIdentity, Capabilities,
  > Lifecycle hooks. No Python objects.
  > **Command:** `g++ -std=c++20 -c tests/test_plugin_abi.cpp -I src/aetherlink/plugins/include/`
  > **Validation:** Exit 0, compiles without errors
  > **Evidence:** `docs/breaking-changes/abi.md` entry created
  > **ARP Trigger:** On compile failure, report exact compiler error before any fix

- [ ] Freeze gRPC proto
  `[IPC-FRZ-01] -> [PRD-§5.9, §4.4]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target File:** `src/aetherlink/proto/capture.proto`
  > **Output Files:** `src/aetherlink/proto/capture_pb2.py`, `capture_pb2_grpc.py`
  > **Test File:** `tests/test_capture_proto.py`
  > **Behavior:** gRPC services for worker control. Control plane separated from data.
  > **Command:** `uv run python -m grpc_tools.protoc -I src/aetherlink/proto/ --python_out=src/aetherlink/proto/ --grpc_python_out=src/aetherlink/proto/ src/aetherlink/proto/capture.proto && uv run pytest tests/test_capture_proto.py -vv`
  > **Validation:** Exit 0, both output files exist, all tests pass
  > **Evidence:** `src/aetherlink/proto/capture_pb2.py` exists; `docs/breaking-changes/proto.md` entry created
  > **ARP Trigger:** On protoc failure, report exact protoc error. On pytest failure, report which assertion failed.

- [ ] Define shared memory layout contract
  `[IPC-SHM-01] -> [PRD-§5.9, §4.4]`
  > **Preconditions:** `[IPC-FRZ-01]` complete
  > **Target File:** `src/aetherlink/core/shared_memory_layout.py`
  > **Test File:** `tests/test_shared_memory_layout.py`
  > **Behavior:** Deterministic ring buffer layout. Offsets validated in Python.
  > **Command:** `uv run pytest tests/test_shared_memory_layout.py -vv`
  > **Validation:** Exit 0, 0 failures
  > **Evidence:** `docs/breaking-changes/shmem.md` entry created
  > **ARP Trigger:** On failure, report which offset assertion failed before fixing

- [ ] Implement remote-play integration stub
  `[CAP-RMP-01] -> [PRD-§5.7]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target Files:** `src/aetherlink/core/remote_play.py`
  > **Test File:** `tests/test_remote_play.py`
  > **Behavior:** Module importable, interfaces defined, plugin contract implemented
  > **Command:** `uv run pytest tests/test_remote_play.py -vv`
  > **Validation:** Exit 0, module importable, interfaces assert pass
  > **Evidence:** `uv run python -c "import aetherlink.core.remote_play"` exits 0
  > **ARP Trigger:** On ImportError, report missing dependency before fixing

- [ ] Complete GPU renderer plugin
  `[UI-GPU-01] -> [PRD-§5.5]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target Files:** `src/aetherlink/plugins/capture/gpu_renderer.py`
  > **Test File:** `tests/test_gpu_renderer_plugin.py`
  > **Behavior:** Replaces placeholder. Pipeline handles output without crashing.
  > **Command:** `uv run pytest tests/test_gpu_renderer_plugin.py -vv`
  > **Validation:** Exit 0, no pipeline crash assertions
  > **Evidence:** No `_stub` markers remain in file
  > **ARP Trigger:** On crash in test, capture traceback before attempting fix

- [ ] Add dependency tracking for environment management
  `[ENV-DEP-01] -> [PRD-§5.10.1]`
  > **Preconditions:** None
  > **Target Files:** `src/aetherlink/core/env_manager.py`
  > **Test File:** `tests/test_dependency_tracking.py`
  > **Behavior:** Tracks dependency count, disk usage. Emits structured data.
  > **Command:** `uv run pytest tests/test_dependency_tracking.py -vv`
  > **Validation:** Exit 0, disk usage + package count assertions pass
  > **Evidence:** Test output confirms structured dict with `dep_count` and `disk_bytes` keys
  > **ARP Trigger:** On assertion failure, report which field is missing or wrong

- [ ] Integrate admin dashboard UI elements
  `[UI-ADM-01] -> [PRD-§5.12]`
  > **Preconditions:** `[ENT-VAL-01]` in Phase 4 spec reviewed
  > **Target Files:** `src/aetherlink/ui/panels/admin_dashboard.py`
  > **Test File:** `tests/test_admin_dashboard.py`
  > **Behavior:** Modal launches, shows mocked entitlement data
  > **Command:** `uv run pytest tests/test_admin_dashboard.py -vv`
  > **Validation:** Exit 0, modal instantiation does not crash
  > **Evidence:** Widget instantiation asserted in test output
  > **ARP Trigger:** On QApplication crash, capture stderr before fixing

### Phase 0 Exit Criteria
`[PLT-EXIT-00] -> [PRD-§4]`

All of the following MUST pass before Phase 1 begins:

```bash
# 1. No placeholder stubs
uv run pytest tests/test_no_placeholders.py

# 2. ABI compiles
g++ -std=c++20 -c tests/test_plugin_abi.cpp -I src/aetherlink/plugins/include/

# 3. Proto generates + tests pass
uv run pytest tests/test_capture_proto.py

# 4. Shared memory layout tests pass
uv run pytest tests/test_shared_memory_layout.py

# 5. Full suite green
uv run ruff check . && uv run pytest tests/ -x
```

> If any command exits non-zero, execute ARP before advancing.
> Codebase MUST be in a runnable state (host boots without crash) before Phase 1.

---

## Phase 1 — UI Shell & Core Framework

### Work Items

- [ ] Deliver basic PySide6 Qt shell
  `[UI-SHL-01] -> [PRD-§6]`
  > **Preconditions:** Phase 0 exit criteria passed
  > **Target Files:** `src/aetherlink/main.py`, `src/aetherlink/ui/main_window.py`
  > **Test File:** `tests/test_ui_shell.py`
  > **Behavior:** `QApplication` initializes, `MainWindow` instantiates without crash.
  > Uses `app.exec()`. Dark theme with purple accents applied.
  > **Command:** `uv run pytest tests/test_ui_shell.py -vv`
  > **Validation:** Exit 0, QApplication init asserted, MainWindow instantiates
  > **Evidence:** `uv run python -c "from aetherlink.ui.main_window import MainWindow"` exits 0
  > **ARP Trigger:** On PySide6 import error, report missing Qt bindings before fixing

- [ ] Sweep and isolate plugin placeholders
  `[ABI-DEV-02] -> [PRD-§5.1]`
  > **Preconditions:** `[ABI-DEV-01]` complete
  > **Target Files:** `src/aetherlink/plugins/capture/_stubs/*`
  > **Behavior:** All stubs fully implemented or removed. No dangling logic schemas.
  > **Command:** `uv run pytest tests/test_no_placeholders.py -vv`
  > **Validation:** Exit 0; `_stubs/` dir empty or absent
  > **Evidence:** `ls src/aetherlink/plugins/capture/_stubs/` returns empty
  > **ARP Trigger:** On failure, list which files remain and why before fixing

- [ ] Isolate or sequence offline grace logic
  `[ENT-GRC-01] -> [PRD-§7]`
  > **Preconditions:** Phase 0 complete
  > **Target Files:** `src/aetherlink/core/grace_period.py`
  > **Test File:** `tests/test_grace_period.py`
  > **Behavior:** Formalized TTL expiry logic. Grace period either implemented
  > correctly or explicitly sequenced to Phase 4.
  > **Command:** `uv run pytest tests/test_grace_period.py -vv`
  > **Validation:** Exit 0, TTL expiry assertion passes
  > **Evidence:** Test confirms `entitlement.locked == True` after TTL expiry
  > **ARP Trigger:** On TTL assertion failure, report actual vs expected expiry time

- [ ] Implement remote-play integrations
  `[CAP-RMP-02] -> [PRD-§5.7]`
  > **Preconditions:** `[CAP-RMP-01]` complete
  > **Target Files:** `src/aetherlink/core/remote_play.py`
  > **Test File:** `tests/test_remote_play.py`
  > **Behavior:** Python module links remote-play to core pipeline. Importable,
  > interfaces concrete.
  > **Command:** `uv run pytest tests/test_remote_play.py -vv`
  > **Validation:** Exit 0, interface method assertions pass
  > **Evidence:** Module importable without error
  > **ARP Trigger:** On interface assertion failure, report which method is missing

- [ ] Complete scripting and inference engine plugins
  `[WRK-INF-01] -> [PRD-§5.8]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target Files:** `src/aetherlink/plugins/inference_engine.py`
  > **Test File:** `tests/test_inference_engine.py`
  > **Behavior:** Scripting and ML inference plugin abstractions. Plugin registration
  > verified.
  > **Command:** `uv run pytest tests/test_inference_engine.py -vv`
  > **Validation:** Exit 0, plugin registration assertions pass
  > **Evidence:** Plugin registers without raising `PluginLoadError`
  > **ARP Trigger:** On registration failure, report which contract method is missing

- [ ] Implement baseline input and output plugin contracts
  `[ABI-IO-01] -> [PRD-§5.2, §5.6]`
  > **Preconditions:** `[ABI-FRZ-01]` complete
  > **Target Files (Python):** `src/aetherlink/input/xinput.py`, `src/aetherlink/output/vigem.py`
  > **Target Files (Native):** `host/plugins/xinput_provider.cpp`, `host/plugins/vigem_output.cpp`
  > **Test File:** `tests/test_io_plugins.py`
  > **Behavior:** Python abstract interfaces for controller state read/write.
  > Native stubs export `Initialize` and `GetCapabilities` per `plugin_system.hpp`.
  > **Command:** `uv run python -c "import aetherlink.input.xinput; import aetherlink.output.vigem" && uv run pytest tests/test_io_plugins.py -vv`
  > **Validation:** Exit 0, both imports succeed, interface tests pass
  > **Evidence:** `uv run python -c "import aetherlink.input.xinput"` exits 0
  > **ARP Trigger:** On ImportError, report missing module path before fixing

- [ ] Test and validate subsystem interactions (split)
  `[ABI-INT-01] -> [PRD-§5.2, §5.4, §5.9]`

  Split into three discrete items:

  - [ ] Capture ↔ Worker integration test
    `[CAP-INT-01] -> [PRD-§5.4, §5.9]`
    > **Command:** `uv run pytest tests/integration/test_capture_worker.py -vv`
    > **Evidence:** Frame handoff assertion passes in test output

  - [ ] Input ↔ Output pipeline integration test
    `[ABI-INT-02] -> [PRD-§5.2]`
    > **Command:** `uv run pytest tests/integration/test_io_pipeline.py -vv`
    > **Evidence:** Latency measurement logged, within 5ms assertion

  - [ ] Entitlement ↔ Plugin loader integration test
    `[ENT-INT-01] -> [PRD-§5.1.3, §7]`
    > **Command:** `uv run pytest tests/integration/test_entitlement_loader.py -vv`
    > **Evidence:** Blocked load logged: `[BLOCKED] premium_plugin.dll — no entitlement`

### Phase 1 Exit Criteria
`[PLT-EXIT-01] -> [PRD-§4]`

```bash
# 1. Qt shell boots
uv run pytest tests/test_ui_shell.py

# 2. No stubs remaining
uv run pytest tests/test_no_placeholders.py

# 3. IO plugin interfaces importable
uv run python -c "import aetherlink.input.xinput; import aetherlink.output.vigem"

# 4. Full suite
uv run ruff check . && uv run pytest tests/ -x
```

---

## Phase 2 — Capture + Worker Integration

### Work Items

- [ ] Deliver OpenCV capture plugin contract
  `[CAP-OCV-01] -> [PRD-§5.4.1]`
  > **Preconditions:** `[IPC-SHM-01]` complete, `[ABI-FRZ-01]` complete
  > **Target File (Python):** `src/aetherlink/vision/cv_capture.py`
  > **Target File (Native):** `host/plugins/cv_capture.cpp`
  > **Test File:** `tests/test_cv_capture.py`
  > **Behavior:** Python module defines interaction with native CV capture plugin.
  > Native plugin stubs frame capture + shared memory mapping.
  > **Command:** `uv run pytest tests/test_cv_capture.py -vv`
  > **Validation:** Exit 0, method signature assertions pass
  > **Evidence:** Module importable; `get_mode_matrix()` returns typed list
  > **ARP Trigger:** On signature mismatch, report expected vs actual method signatures

- [ ] Implement capability matrix filtering contract
  `[CAP-MAT-01] -> [PRD-§5.4.2]`
  > **Preconditions:** `[CAP-OCV-01]` complete
  > **Target Files:** `host/capability_matrix_filtering.cpp`, `include/capability_matrix_filtering.h`
  > **Test File:** `tests/test_capability_matrix.cpp`
  > **Behavior:** Host rejects plugin capabilities not matching expected schema.
  > Mode descriptor fields validated (width, height, fps, pixel_format, zero_copy, hdr).
  > **Command:** `g++ -std=c++20 tests/test_capability_matrix.cpp -I include/ && ./a.out`
  > **Validation:** Exit 0, all capability rejection assertions pass
  > **Evidence:** Compile output clean; test runner exits 0
  > **ARP Trigger:** On compile error, report exact g++ error before fixing

- [ ] Implement worker supervisor + IPC
  `[WRK-SUP-01] -> [PRD-§5.9]`
  > **Preconditions:** `[IPC-FRZ-01]` complete, `[IPC-SHM-01]` complete
  > **Target Files:** `host/worker_supervisor.cpp`, `src/aetherlink/core/supervisor.py`
  > **Test File:** `tests/test_supervisor.py`
  > **Behavior:** Start/monitor (heartbeat)/stop Python worker via subprocess + gRPC.
  > Crash recovery with backoff. Restart within 3s.
  > **Command:** `uv run pytest tests/test_supervisor.py -vv`
  > **Validation:** Exit 0, spawn + termination assertions pass, restart < 3s asserted
  > **Evidence:** Test log shows `[WRK] restart completed in <Xs>` where X < 3
  > **ARP Trigger:** On heartbeat timeout in test, report subprocess state before fixing

- [ ] Add performance HUD panel
  `[UI-HUD-01] -> [PRD-§6]`
  > **Preconditions:** `[UI-SHL-01]` complete
  > **Target File:** `src/aetherlink/ui/panels/performance_hud.py`
  > **Test File:** `tests/test_performance_hud.py`
  > **Behavior:** PySide6 widget shows real-time FPS, latency, resource metrics.
  > Never blocks UI thread > 16ms.
  > **Command:** `uv run pytest tests/test_performance_hud.py -vv`
  > **Validation:** Exit 0, widget instantiation + default value assertions pass
  > **Evidence:** Widget renders without blocking assertion in test output
  > **ARP Trigger:** On instantiation crash, report Qt error before fixing

### Phase 2 Exit Criteria
`[PLT-EXIT-02] -> [PRD-§4]`

```bash
# 1. Capture contract
uv run pytest tests/test_cv_capture.py

# 2. Capability matrix compiles + passes
g++ -std=c++20 tests/test_capability_matrix.cpp -I include/ && ./a.out

# 3. Supervisor spawn/restart
uv run pytest tests/test_supervisor.py

# 4. Full suite
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
  > **Behavior:** Programmatically creates isolated `.venv` dirs using `uv`.
  > Exposes: Python version, dep count, disk usage, last updated, validation status.
  > **Command:** `uv run pytest tests/test_env_manager.py -vv`
  > **Validation:** Exit 0, `subprocess.run` mock asserts `uv venv` called correctly
  > **Evidence:** Mock call args include `uv`, `venv`, target path
  > **ARP Trigger:** On mock assertion failure, report actual call args before fixing

- [ ] Deliver environment bundle installer contract
  `[ENV-BUN-01] -> [PRD-§5.10.2]`
  > **Preconditions:** `[ENV-MGR-01]` complete
  > **Target File:** `src/aetherlink/core/bundle_installer.py`
  > **Test File:** `tests/test_bundle_installer.py`
  > **Behavior:** Extracts zipped bundle, verifies `manifest.json`, streams install
  > logs to UI. One-click install. Supports CPU + CUDA variants.
  > **Command:** `uv run pytest tests/test_bundle_installer.py -vv`
  > **Validation:** Exit 0, tempfile + zipfile extraction assertions pass
  > **Evidence:** Test confirms manifest fields: `python_version`, `deps`, `variant`
  > **ARP Trigger:** On extraction failure, report which manifest field is missing

- [ ] Implement signed artifact verification contract
  `[RES-SIG-01] -> [PRD-§5.11.2]`
  > **Preconditions:** Phase 0 complete
  > **Target Files:** `host/artifact_verifier.cpp`, `src/aetherlink/core/security.py`
  > **Test File:** `tests/test_security.py`
  > **Behavior:** Enforces SHA-256 + signature checks on all artifacts.
  > Valid hash passes. Mismatch hash raises `ArtifactIntegrityError`.
  > **Command:** `uv run pytest tests/test_security.py -vv`
  > **Validation:** Exit 0, valid hash passes, mismatch hash raises correct exception
  > **Evidence:** Both positive and negative path assertions logged in test output
  > **ARP Trigger:** On wrong exception type, report actual vs expected exception

- [ ] Add resource browsing UI panel
  `[UI-RES-01] -> [PRD-§5.11, §6]`
  > **Preconditions:** `[RES-SIG-01]` complete, `[UI-SHL-01]` complete
  > **Target File:** `src/aetherlink/ui/panels/online_resources.py`
  > **Test File:** `tests/test_online_resources.py`
  > **Behavior:** PySide6 modal bridges catalog metadata into visual list.
  > One-click install. Streamed install logs. Clear success/failure states.
  > **Command:** `uv run pytest tests/test_online_resources.py -vv`
  > **Validation:** Exit 0, mock JSON responses render correctly in widget
  > **Evidence:** Widget list count matches mock catalog item count in assertion
  > **ARP Trigger:** On widget render failure, capture Qt error before fixing

### Phase 3 Exit Criteria
`[PLT-EXIT-03] -> [PRD-§4]`

```bash
# 1. Env manager mocks pass
uv run pytest tests/test_env_manager.py

# 2. Bundle installer
uv run pytest tests/test_bundle_installer.py

# 3. Security / artifact verification
uv run pytest tests/test_security.py

# 4. Full suite
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
  > **Behavior:** Validates JWT + local cache for tier assignments.
  > Offline grace TTL enforced. State machine: `LOCKED → GRACE → ELIGIBLE → LOADED`.
  > **Command:** `uv run pytest tests/test_entitlement_check.py -vv`
  > **Validation:** Exit 0, mocked JWT payload assertions pass for all states
  > **Evidence:** All 4 state transitions logged in test output
  > **ARP Trigger:** On wrong state transition, report actual vs expected state

- [ ] Implement premium plugin gating contract
  `[ENT-GAT-01] -> [PRD-§5.1.3]`
  > **Preconditions:** `[ENT-VAL-01]` complete, `[ABI-FRZ-01]` complete
  > **Target Files (Native):** `host/plugin_loader.cpp`
  > **Test File:** `tests/test_plugin_loader.cpp`
  > **Behavior:** Refuses to map premium DLLs into memory without entitlement.
  > Routes to purchase flow on block. Log output: `[BLOCKED] <dll> — no entitlement`.
  > **Command:** `g++ -std=c++20 tests/test_plugin_loader.cpp && ./a.out`
  > **Validation:** Exit 0, blocked load assertion passes, purchase flow route asserted
  > **Evidence:** Test log contains `[BLOCKED]` string for premium DLL attempt
  > **ARP Trigger:** On DLL loaded without token, report which gate was bypassed

- [ ] Deliver admin APIs contract
  `[PLT-ADM-01] -> [PRD-§5.12]`
  > **Preconditions:** `[ENT-VAL-01]` complete
  > **Target File:** `src/aetherlink/core/admin_api.py`
  > **Test File:** `tests/test_admin_api.py`
  > **Behavior:** REST/RPC endpoints for user management, entitlement assignment,
  > session revocation, audit log. All return standardized JSON.
  > **Command:** `uv run pytest tests/test_admin_api.py -vv`
  > **Validation:** Exit 0, all endpoint JSON schema assertions pass
  > **Evidence:** Each endpoint test logs response schema match
  > **ARP Trigger:** On schema mismatch, report expected vs actual JSON keys

- [ ] Implement offline grace logic contract
  `[ENT-GRC-02] -> [PRD-§7]`
  > **Preconditions:** `[ENT-VAL-01]` complete, `[ENT-GRC-01]` complete
  > **Target File:** `src/aetherlink/core/grace_period.py`
  > **Test File:** `tests/test_grace_period_logic.py`
  > **Behavior:** Caches entitlement state with TTL. On TTL expiry, premium locks.
  > Base features remain usable. TTL range: 7–30 days.
  > **Command:** `uv run pytest tests/test_grace_period_logic.py -vv`
  > **Validation:** Exit 0, time-travel test confirms lock at TTL expiry
  > **Evidence:** `entitlement.locked == True` asserted after simulated expiry
  > **ARP Trigger:** On TTL calculation error, report actual vs expected expiry timestamp

### Phase 4 Exit Criteria
`[PLT-EXIT-04] -> [PRD-§4, §7]`

```bash
# 1. Entitlement state machine
uv run pytest tests/test_entitlement_check.py

# 2. Plugin gating
g++ -std=c++20 tests/test_plugin_loader.cpp && ./a.out

# 3. Grace period TTL
uv run pytest tests/test_grace_period_logic.py

# 4. Full suite — zero failures required before release
uv run ruff check . && uv run pytest tests/ --tb=short
```

---

## Part 3 — New Files to Create

### 3.1 AGENTS.md `[PLT-AGT-01] -> [PRD-§4]`

Create `AGENTS.md` at repo root. This is the persistent context file consumed
by every agent session.

```markdown
# AGENTS.md — Aetherlink Specialist Context

## Persona
- **Role:** Senior Windows Systems Engineer
- **Stack:** C++20 (native plugins), Python 3.12 (workers + UI), PySide6 6.9.x
- **Style:** Concise, type-hinted, Google-format docstrings, Loguru logging
- **Testing:** TDD always — test first, prove failure, implement, prove pass

## Environment (Windows 11)
- **Package manager:** `uv` — never use `pip` directly
- **Python version:** 3.12
- **Linter/Formatter:** `ruff` (88-char line length)
- **Commands:**
  - Sync: `uv sync`
  - Test: `uv run pytest`
  - Lint: `uv run ruff check .`
  - Format: `uv run ruff format .`

## Frozen Contracts (DO NOT MODIFY)
- `src/aetherlink/plugins/include/plugin_system.hpp`
- `src/aetherlink/proto/capture.proto`
- `src/aetherlink/core/shared_memory_layout.py`

## Boundaries
| Rule | Detail |
|---|---|
| NEVER | Load premium DLL without entitlement token |
| NEVER | Execute unsigned artifact |
| NEVER | Write to `src/plugins/*` |
| NEVER | Use `print()` — use `loguru.logger` |
| NEVER | Modify frozen contracts without human sign-off |
| ASK FIRST | Any frozen contract change |
| ASK FIRST | Entitlement state machine semantics |
| ALWAYS | TDD — test first |
| ALWAYS | `uv run ruff check && uv run pytest` before done |
| ALWAYS | Google-format docstrings + type hints |

## Atomic Recovery Protocol (ARP)
On any validation failure:
1. CAPTURE: `git diff > _recovery/failed_state_<timestamp>.patch`
2. ANALYZE: `uv run ruff check <file> && uv run pytest <test> -vv`
3. REPORT: State exactly why it failed before touching code
4. FIX: One attempt only
5. REVERT: If fix fails, `git checkout -- <files>`, report BLOCKED
```

### 3.2 `_recovery/` Directory

Create `_recovery/.gitkeep` at repo root. This is the ARP staging area for
failed state patches. Add `_recovery/*.patch` to `.gitignore`.

---

## Traceability Index

Quick-reference: PRD section → all related PLAN items.

| PRD Section | Traceability IDs |
|---|---|
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

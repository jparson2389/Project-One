# Shared Memory Layout

## Purpose
This document freezes the Phase 0 shared-memory contract between capture producers and downstream consumers. The transport is a deterministic ring buffer with fixed-size slots.

## Ring Header
The ring starts with a fixed logical header represented in Python by `aetherlink.core.shared_memory_layout.FrameRingHeader`.

Fields:
- `magic`: fixed byte signature `AETHFRM1`.
- `layout_version`: integer version (`1` for this freeze).
- `width`: frame width in pixels.
- `height`: frame height in pixels.
- `pixel_format`: one of `BGR24`, `BGRA32`, `RGBA32`, `NV12`, `GRAY8`.
- `slot_count`: number of frame slots in the ring (minimum `2`).
- `slot_stride_bytes`: aligned slot size in bytes.

## Slot Rules
Each slot follows these rules:
- Slot payload length equals `slot_stride_bytes`.
- Slot offsets are contiguous and deterministic.
- Both offsets and stride are aligned to `64` bytes.
- Slot payload always holds a complete frame.

Alignment formula:
- `raw_size = width * height * bytes_per_pixel(pixel_format)`
- `slot_stride_bytes = ceil(raw_size / 64) * 64`

## Deterministic Layout
`aetherlink.core.shared_memory_layout.build_layout(...)` is the canonical builder.
It returns:
- validated header
- `slot_count` validated descriptors
- contiguous offsets (`0`, `stride`, `2*stride`, ...)

## Validation Invariants
The layout is invalid if any of the following happens:
- header magic or version mismatch
- non-positive dimensions
- slot count < 2
- unaligned stride/offset
- stride too small for one frame
- descriptor count mismatch
- non-contiguous slot offsets

## Compatibility Notes
- This document and `shared_memory_layout.py` are the source of truth for Phase 0 shared-memory freeze.
- Future changes must bump `layout_version` and preserve backward compatibility handling in runtime loaders.

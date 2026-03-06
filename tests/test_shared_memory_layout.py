from __future__ import annotations

import pytest

from aetherlink.core.shared_memory_layout import (
    SLOT_ALIGNMENT_BYTES,
    FrameRingHeader,
    build_layout,
    expected_slot_size_bytes,
)


def test_expected_slot_size_is_aligned() -> None:
    size = expected_slot_size_bytes(width=1920, height=1080, pixel_format='BGR24')
    assert size % SLOT_ALIGNMENT_BYTES == 0


def test_build_layout_creates_contiguous_offsets() -> None:
    layout = build_layout(
        width=1280,
        height=720,
        pixel_format='BGRA32',
        slot_count=3,
    )
    assert len(layout.slots) == 3
    assert layout.slots[0].offset_bytes == 0
    assert layout.slots[1].offset_bytes == layout.header.slot_stride_bytes
    assert layout.slots[2].offset_bytes == layout.header.slot_stride_bytes * 2


def test_header_rejects_bad_magic() -> None:
    header = FrameRingHeader(
        width=640,
        height=480,
        pixel_format='GRAY8',
        slot_count=2,
        slot_stride_bytes=expected_slot_size_bytes(
            width=640,
            height=480,
            pixel_format='GRAY8',
        ),
        magic=b'INVALID!',
    )

    with pytest.raises(ValueError, match='Invalid ring magic'):
        header.validate()

"""Shared memory frame ring buffer layout and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SLOT_ALIGNMENT_BYTES = 64
RING_LAYOUT_VERSION = 1
RING_MAGIC = b'AETHFRM1'


type PixelFormat = Literal['BGR24', 'BGRA32', 'RGBA32', 'NV12', 'GRAY8']


_BYTES_PER_PIXEL: dict[PixelFormat, int] = {
    'BGR24': 3,
    'BGRA32': 4,
    'RGBA32': 4,
    'NV12': 2,
    'GRAY8': 1,
}


@dataclass(slots=True, frozen=True)
class FrameRingHeader:
    """Logical header used by host and worker for frame ring coordination."""

    width: int
    height: int
    pixel_format: PixelFormat
    slot_count: int
    slot_stride_bytes: int
    layout_version: int = RING_LAYOUT_VERSION
    magic: bytes = RING_MAGIC

    def validate(self) -> None:
        """Validate structural invariants for the ring header."""
        if self.magic != RING_MAGIC:
            msg = 'Invalid ring magic.'
            raise ValueError(msg)
        if self.layout_version != RING_LAYOUT_VERSION:
            msg = 'Unsupported ring layout version.'
            raise ValueError(msg)
        if self.width <= 0 or self.height <= 0:
            msg = 'Frame dimensions must be positive.'
            raise ValueError(msg)
        if self.slot_count < 2:
            msg = 'slot_count must be at least 2 for producer/consumer overlap.'
            raise ValueError(msg)
        if self.slot_stride_bytes <= 0:
            msg = 'slot_stride_bytes must be positive.'
            raise ValueError(msg)
        if self.slot_stride_bytes % SLOT_ALIGNMENT_BYTES != 0:
            msg = 'slot_stride_bytes must be aligned to 64 bytes.'
            raise ValueError(msg)

        minimum_stride = expected_slot_size_bytes(
            width=self.width,
            height=self.height,
            pixel_format=self.pixel_format,
        )
        if self.slot_stride_bytes < minimum_stride:
            msg = 'slot_stride_bytes is too small for one full frame.'
            raise ValueError(msg)


@dataclass(slots=True, frozen=True)
class FrameSlotDescriptor:
    """Descriptor for one slot payload in the shared-memory ring."""

    slot_index: int
    offset_bytes: int
    length_bytes: int

    def validate(self, *, slot_count: int, slot_stride_bytes: int) -> None:
        """Validate descriptor alignment and containment within the ring."""
        if self.slot_index < 0 or self.slot_index >= slot_count:
            msg = 'slot_index out of range.'
            raise ValueError(msg)
        if self.offset_bytes < 0:
            msg = 'offset_bytes must be non-negative.'
            raise ValueError(msg)
        if self.length_bytes <= 0:
            msg = 'length_bytes must be positive.'
            raise ValueError(msg)
        if self.length_bytes > slot_stride_bytes:
            msg = 'length_bytes exceeds slot_stride_bytes.'
            raise ValueError(msg)
        if self.offset_bytes % SLOT_ALIGNMENT_BYTES != 0:
            msg = 'offset_bytes must be 64-byte aligned.'
            raise ValueError(msg)


@dataclass(slots=True, frozen=True)
class SharedMemoryLayout:
    """A full ring layout contract used by capture and consumer workers."""

    header: FrameRingHeader
    slots: tuple[FrameSlotDescriptor, ...]

    def validate(self) -> None:
        """Validate layout invariants for the header and slot descriptors."""
        self.header.validate()
        if len(self.slots) != self.header.slot_count:
            msg = 'Slot descriptor count does not match header slot_count.'
            raise ValueError(msg)

        expected_offset = 0
        for descriptor in self.slots:
            descriptor.validate(
                slot_count=self.header.slot_count,
                slot_stride_bytes=self.header.slot_stride_bytes,
            )
            if descriptor.offset_bytes != expected_offset:
                msg = 'Slot offsets must be contiguous and deterministic.'
                raise ValueError(msg)
            expected_offset += self.header.slot_stride_bytes


def expected_slot_size_bytes(
    *, width: int, height: int, pixel_format: PixelFormat
) -> int:
    """Return frame payload size rounded up to 64-byte slot alignment."""
    if width <= 0 or height <= 0:
        msg = 'Dimensions must be positive.'
        raise ValueError(msg)

    bytes_per_pixel = _BYTES_PER_PIXEL[pixel_format]
    raw_size = width * height * bytes_per_pixel
    remainder = raw_size % SLOT_ALIGNMENT_BYTES
    if remainder == 0:
        return raw_size
    return raw_size + (SLOT_ALIGNMENT_BYTES - remainder)


def build_layout(
    *,
    width: int,
    height: int,
    pixel_format: PixelFormat,
    slot_count: int,
) -> SharedMemoryLayout:
    """Build a deterministic contiguous shared-memory frame ring layout."""
    slot_stride_bytes = expected_slot_size_bytes(
        width=width,
        height=height,
        pixel_format=pixel_format,
    )
    header = FrameRingHeader(
        width=width,
        height=height,
        pixel_format=pixel_format,
        slot_count=slot_count,
        slot_stride_bytes=slot_stride_bytes,
    )
    slots = tuple(
        FrameSlotDescriptor(
            slot_index=index,
            offset_bytes=index * slot_stride_bytes,
            length_bytes=slot_stride_bytes,
        )
        for index in range(slot_count)
    )
    layout = SharedMemoryLayout(header=header, slots=slots)
    layout.validate()
    return layout

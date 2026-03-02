"""Shared memory frame and ring buffer models for inter-process data transport."""

from __future__ import annotations

import pydantic


class SharedMemoryFrame(pydantic.BaseModel):
    """A single captured frame stored in shared memory.

    Attributes:
        frame_id: Monotonically increasing frame identifier.
        data: Raw frame bytes.

    """

    frame_id: int
    data: bytes


class SharedMemoryRingBuffer(pydantic.BaseModel):
    """Ring buffer holding a fixed-capacity sequence of shared memory frames.

    Attributes:
        frames: Ordered list of frames currently in the buffer.
        capacity: Maximum number of frames the buffer can hold.

    """

    frames: list[SharedMemoryFrame]
    capacity: int

import pydantic

class SharedMemoryFrame(pydantic.BaseModel):
    '''A class representing a frame in shared memory."
    frame_id: int
    data: bytes


class SharedMemoryRingBuffer(pydantic.BaseModel):
    '''A class representing a ring buffer for shared memory frames."
    frames: list[SharedMemoryFrame]
    capacity: int
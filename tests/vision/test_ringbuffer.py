import numpy as np

from vision.core.ringbuffer import FrameRingBuffer


def frame(value):
    return np.full((4, 4, 3), value, dtype=np.uint8)


def test_capacity_is_seconds_times_fps():
    assert FrameRingBuffer(seconds=10, fps=2).capacity == 20


def test_keeps_only_the_most_recent_frames():
    buf = FrameRingBuffer(seconds=2, fps=2)   # capacidad 4

    for i in range(6):
        buf.push(frame(i))

    kept = [int(f[0, 0, 0]) for f in buf.frames()]
    assert kept == [2, 3, 4, 5]


def test_frames_is_empty_before_any_push():
    assert FrameRingBuffer(seconds=5, fps=2).frames() == []

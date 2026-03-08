from memory.runtime_memory import AgentMemoryRecorder, NullMemoryRecorder


def test_null_memory_recorder_noop():
    recorder = NullMemoryRecorder()
    recorder.remember("hello", important=True)


def test_agent_memory_recorder_accepts_calls_without_runtime():
    recorder = AgentMemoryRecorder("research")
    recorder.remember("event", important=False)

from capture.cursor_tracker import describe_cursor, relative_position
from core.session import TranscriptBuffer
from speech.trigger_detector import TriggerDetector


def test_relative_cursor():
    assert relative_position(960, 540, 0, 0, 1920, 1080) == (0.5, 0.5)
    assert relative_position(2000 + 100, 50, 1920, 0, 1000, 500) == (0.18, 0.1)
    assert relative_position(-50, 5000, 0, 0, 100, 100) == (0.0, 1.0)  # clamped
    assert "64% width" in describe_cursor((0.64, 0.42))


def test_transcript_buffer_keeps_recent_only():
    buf = TranscriptBuffer(seconds=45)
    buf.add("old sentence", at=0)
    buf.add("recent sentence", at=50)
    assert buf.recent_text(now=60) == "recent sentence"
    assert buf.recent_text(now=200) == ""


def test_pinned_demo_transcript_used_when_empty():
    buf = TranscriptBuffer(seconds=45)
    buf.set_pinned("demo")
    assert buf.recent_text() == "demo"


def test_trigger_detection():
    d = TriggerDetector(cooldown_seconds=0)
    assert d.check("visualize this", now=1)
    assert d.check("Visualize this line", now=2)
    assert d.check("can you visualize this", now=3)
    assert d.check("the normal sentence without trigger", now=4) is None


def test_trigger_debounce():
    d = TriggerDetector(cooldown_seconds=8)
    assert d.check("visualize this", now=0)
    assert d.check("please visualize this", now=3) is None   # inside cooldown
    assert d.check("please visualize this", now=20)          # cooldown over

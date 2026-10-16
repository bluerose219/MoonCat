"""효과음. 음표를 직접 합성해 WAV로 만들고 윈도우 내장 winsound로 재생한다.

외부 파일·라이브러리 없음. 윈도우가 아니면 조용히 아무 소리도 내지 않는다.
"""
import struct
import wave
import zlib

from . import save_manager

try:
    import winsound
except ImportError:
    winsound = None

RATE = 22050

# (주파수 Hz, 길이 초). 주파수 0은 쉼표.
NOTES = {
    "step": [(392, .04)],
    "find": [(784, .07), (1047, .12)],
    "fail": [(196, .12)],
    "repair": [(523, .06), (659, .06), (784, .1)],
    "faint": [(392, .1), (311, .1), (233, .25)],
    "event": [(587, .08), (0, .04), (880, .14)],
    "achieve": [(784, .07), (988, .07), (1175, .07), (1568, .2)],
    "launch": [(150 + i * 45, .035) for i in range(30)],
    "gameover": [(392, .18), (0, .05), (370, .18), (0, .05), (349, .18), (0, .05), (330, .5)],
}

# 한 번에 여러 소리가 쌓이면 가장 중요한 것 하나만 낸다
PRIORITY = ["launch", "gameover","achieve", "faint", "event", "repair", "find", "fail", "step"]


def _samples(notes):
    for freq, dur in notes:
        n = int(RATE * dur)
        for i in range(n):
            if not freq:
                yield 0
                continue
            env = min(1.0, i / 150, (n - i) / 300)   # 딸깍 소리 방지
            square = 1 if (freq * i / RATE) % 1 < 0.5 else -1
            yield int(6000 * env * square)


class Sound:
    def __init__(self, muted: bool = False):
        self.muted = muted
        self.dir = save_manager.SAVE_DIR / "sounds"

    def _file(self, name: str):
        notes = NOTES[name]
        path = self.dir / f"{name}-{zlib.crc32(repr(notes).encode()):08x}.wav"
        if not path.exists():
            self.dir.mkdir(parents=True, exist_ok=True)
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes(b"".join(struct.pack("<h", s) for s in _samples(notes)))
        return path

    def play_queue(self, names: list[str]) -> None:
        for name in PRIORITY:
            if name in names:
                self.play(name)
                break
        names.clear()

    def stop(self) -> None:
        if winsound is not None:
            winsound.PlaySound(None, 0)

    def play(self, name: str) -> None:
        if self.muted or winsound is None or name not in NOTES:
            return
        try:
            winsound.PlaySound(str(self._file(name)),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except (OSError, RuntimeError):
            pass

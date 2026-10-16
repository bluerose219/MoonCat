"""게임 그림 불러오기.

모든 그림은 game/assets/의 PNG다. art/ 폴더의 원본을 tools/make_assets.py가 가공해 만든다.
(tkinter가 PNG를 직접 읽으므로 게임 실행에는 Pillow가 필요 없다)
"""
import tkinter as tk
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
ASSET_NAMES = ("cat", "rabbit", "background", "rocket", "lock_1", "lock_2", "lock_3", "lock_4")


def load_all() -> dict[str, tk.PhotoImage]:
    """Tk 창이 만들어진 뒤에 호출해야 한다. 반환값을 계속 들고 있어야 그림이 사라지지 않는다."""
    return {name: tk.PhotoImage(file=str(ASSETS / f"{name}.png")) for name in ASSET_NAMES}

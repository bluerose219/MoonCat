"""팝업 창들: 이벤트 선택지, 난이도 선택, 엔딩, 기록과 업적."""
import tkinter as tk
from tkinter import ttk

from .config import DIFFICULTIES, REPAIR_REQUIREMENTS
from .events import ENDINGS, GAME_OVER
from .records import ACHIEVEMENTS, Records
from .state import GameState

FONT = ("맑은 고딕", 10)
FONT_BOLD = ("맑은 고딕", 11, "bold")
FONT_TITLE = ("맑은 고딕", 15, "bold")
FONT_SMALL = ("맑은 고딕", 9)


class _Modal(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str, closable: bool = True):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.body = ttk.Frame(self, padding=20)
        self.body.pack(fill="both", expand=True)
        if not closable:
            self.protocol("WM_DELETE_WINDOW", lambda: None)

    def show(self) -> None:
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.focus_set()


def ask_difficulty(parent: tk.Misc, cancellable: bool) -> str | None:
    dlg = _Modal(parent, "난이도 선택", closable=cancellable)
    result: dict[str, str | None] = {"value": None}
    ttk.Label(dlg.body, text="어떤 달에 떨어질까요?", font=FONT_TITLE).pack(anchor="w", pady=(0, 10))

    var = tk.StringVar(value="normal")
    for key, d in DIFFICULTIES.items():
        text = f"{d['name']}  —  {d['desc']}, {d['max_faints']}번 기절하면 게임오버"
        ttk.Radiobutton(dlg.body, text=text, variable=var, value=key).pack(anchor="w", pady=2)

    def choose():
        result["value"] = var.get()
        dlg.destroy()

    row = ttk.Frame(dlg.body)
    row.pack(fill="x", pady=(14, 0))
    ttk.Button(row, text="시작", command=choose).pack(side="right")
    if cancellable:
        ttk.Button(row, text="취소", command=dlg.destroy).pack(side="right", padx=6)
    dlg.show()
    parent.wait_window(dlg)
    return result["value"]


class EventDialog(_Modal):
    """선택을 해야만 닫힌다. 고르기 전에 게임을 꺼도 pending_event로 저장돼 다시 뜬다."""

    def __init__(self, parent, game, on_choose):
        ev = game.current_event()
        super().__init__(parent, ev["title"], closable=False)
        ttk.Label(self.body, text=ev["title"], font=FONT_TITLE).pack(anchor="w")
        ttk.Label(self.body, text=ev["text"], font=FONT, wraplength=380, justify="left").pack(anchor="w", pady=(8, 14))

        for i, choice in enumerate(ev["choices"]):
            text = choice["label"]
            cost = game.choice_cost_text(choice)
            if cost:
                text += f"   ({cost})"
            btn = ttk.Button(self.body, text=text, command=lambda i=i: self._pick(on_choose, i))
            if not game.choice_available(choice):
                btn.config(text=f"🔒 {choice.get('lock_hint', '아직 고를 수 없다')}", state="disabled")
            btn.pack(fill="x", pady=3, ipady=3)
        self.show()

    def _pick(self, on_choose, index):
        self.destroy()
        on_choose(index)


class EndingDialog(_Modal):
    def __init__(self, parent, state: GameState, records: Records, on_new_game):
        title, text = ENDINGS[state.ending_type or "normal"]
        super().__init__(parent, "귀환 성공!")
        ttk.Label(self.body, text=f"엔딩 · {title}", font=FONT_TITLE).pack(anchor="w")
        ttk.Label(self.body, text=text.format(day=state.day), font=FONT, wraplength=380,
                  justify="left").pack(anchor="w", pady=(8, 12))

        diff = DIFFICULTIES.get(state.difficulty, DIFFICULTIES["normal"])["name"]
        stats = (f"걸린 날: {state.day}일   ·   난이도: {diff}   ·   기절: {state.faint_count}번\n"
                 f"최단 귀환 기록: {records.best_days}일   ·   총 귀환: {records.clears}번")
        ttk.Label(self.body, text=stats, font=FONT_SMALL, foreground="gray").pack(anchor="w")

        row = ttk.Frame(self.body)
        row.pack(fill="x", pady=(16, 0))
        ttk.Button(row, text="새 게임", command=lambda: (self.destroy(), on_new_game())).pack(side="right")
        ttk.Button(row, text="닫기", command=self.destroy).pack(side="right", padx=6)
        self.show()


class GameOverDialog(_Modal):
    def __init__(self, parent, state: GameState, records: Records, on_new_game):
        title, text = GAME_OVER
        super().__init__(parent, "게임오버")
        ttk.Label(self.body, text=f"게임오버 · {title}", font=FONT_TITLE, foreground="#c0392b").pack(anchor="w")
        ttk.Label(self.body, text=text, font=FONT, wraplength=380, justify="left").pack(anchor="w", pady=(8, 12))

        diff = DIFFICULTIES.get(state.difficulty, DIFFICULTIES["normal"])["name"]
        installed = sum(state.installed.values())
        stats = (f"버틴 날: {state.day}일   ·   난이도: {diff}   ·   기절: {state.faint_count}번\n"
                 f"로켓 수리: {installed}/{sum(REPAIR_REQUIREMENTS.values())} 부품   ·   지금까지 게임오버 {records.game_overs}번")
        ttk.Label(self.body, text=stats, font=FONT_SMALL, foreground="gray").pack(anchor="w")

        row = ttk.Frame(self.body)
        row.pack(fill="x", pady=(16, 0))
        ttk.Button(row, text="다시 도전", command=lambda: (self.destroy(), on_new_game())).pack(side="right")
        ttk.Button(row, text="닫기", command=self.destroy).pack(side="right", padx=6)
        self.show()


class RecordsDialog(_Modal):
    def __init__(self, parent, records: Records):
        super().__init__(parent, "기록과 업적")
        ttk.Label(self.body, text="기록", font=FONT_TITLE).pack(anchor="w")
        best = f"{records.best_days}일" if records.best_days else "아직 없음"
        ttk.Label(self.body, text=f"총 귀환 {records.clears}번   ·   최단 귀환 {best}   ·   게임오버 {records.game_overs}번",
                  font=FONT).pack(anchor="w", pady=(4, 14))

        ttk.Label(self.body, text=f"업적  {len(records.achievements)} / {len(ACHIEVEMENTS)}", font=FONT_TITLE).pack(anchor="w")
        for aid, (name, desc) in ACHIEVEMENTS.items():
            got = aid in records.achievements
            row = ttk.Frame(self.body)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text="★" if got else "☆", font=FONT_BOLD,
                      foreground="#d99a1e" if got else "gray").pack(side="left")
            ttk.Label(row, text=name if got else "???", font=FONT_BOLD, width=12).pack(side="left", padx=(6, 0))
            ttk.Label(row, text=desc, font=FONT_SMALL, foreground="black" if got else "gray").pack(side="left")
        ttk.Button(self.body, text="닫기", command=self.destroy).pack(anchor="e", pady=(14, 0))
        self.show()

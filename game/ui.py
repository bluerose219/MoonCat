"""tkinter 메인 화면. 진행 데이터를 직접 들고 있지 않고, 매번 GameState를 읽어 다시 그린다.
(고양이 걷는 위치, 로켓 상승 높이 같은 애니메이션 값만 화면 쪽에 잠깐 둔다.)
"""
import math
import random
import tkinter as tk
from tkinter import messagebox, ttk

from . import dialogs, save_manager, sprites
from .config import CONSUMABLES, DIFFICULTIES, ITEMS, LOCATIONS, MAX_ENERGY, MAX_OXYGEN, REPAIR_REQUIREMENTS
from .dialogs import FONT, FONT_BOLD, FONT_SMALL
from .events import ENDINGS
from .logic import INTRO, Game
from .records import ACHIEVEMENTS
from .sound import Sound
from .state import GameState

# 아래 좌표는 game/assets/background.png 기준 (tools/make_assets.py가 출력해 주는 값)
CANVAS_W, CANVAS_H = 760, 322
FEET_Y = 241           # 고양이가 서는 높이 (받침대 위)
LABEL_Y = 277          # 지역 이름
PERCENT_Y = 254        # 로켓 수리 %
ROCKET_POS = (34, 114) # 로켓 그림 왼쪽 위
ROCKET_SIZE = (65, 113)
LOCK_POS = {"crater": (231, 218), "ice_cave": (386, 218), "probe": (532, 218), "far_side": (678, 218)}
BASE_CAT_OFFSET = 66   # 기지에서는 로켓 옆에 선다
RABBIT_OFFSET = 50     # 동료 달토끼와 고양이 사이 거리 (기지에선 오른쪽, 그 밖엔 왼쪽)
ROCKET_GONE = 260      # 이만큼 올라가면 화면 밖
WALK_SPEED = 10        # 프레임당 픽셀
FRAME_MS = 16
OUTLINE = "#1c1636"


class MoonCatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("문캣 - 달에서 집으로")
        self.resizable(False, False)

        self.records = save_manager.load_records()
        state = save_manager.load()
        self.game = Game(state or GameState())
        self.sound = Sound(muted=self.records.muted)
        self.sprites = sprites.load_all()

        # 화면 전용(저장 안 함) 애니메이션 상태
        self.cat_x = self._cat_target()
        self.cat_hop = 0.0
        self.rocket_lift = ROCKET_GONE if self.game.state.ending else 0
        self._walk_job = None
        self._ending_shown = self.game.state.ending
        self._gameover_shown = self.game.state.game_over
        self._event_open = False
        self._closed = False

        self._build_style()
        self._build_menu()
        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        if state is None:
            self.game.log(INTRO)
            self.after(200, self.first_run)
        else:
            self.game.log("저장된 여정을 이어서 시작한다.")
            self.after(200, self.show_event_if_pending)
        self.persist()
        self.refresh()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2 - 30      # 작업 표시줄 몫만큼 살짝 위로
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    # ---------- 화면 구성 ----------
    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        for name, color in (("O2", "#2d9cdb"), ("Energy", "#f2a33a"), ("Repair", "#e05a47"), ("Low", "#d63c3c")):
            style.configure(f"{name}.Horizontal.TProgressbar", background=color, troughcolor="#e4e6ec",
                            bordercolor="#c9ccd5", lightcolor=color, darkcolor=color)

    def _build_menu(self):
        menubar = tk.Menu(self)
        game_menu = tk.Menu(menubar, tearoff=False)
        game_menu.add_command(label="새 게임", command=self.new_game)
        game_menu.add_command(label="기록과 업적", command=lambda: dialogs.RecordsDialog(self, self.records))
        self.muted_var = tk.BooleanVar(value=self.records.muted)
        game_menu.add_checkbutton(label="소리 끄기", variable=self.muted_var, command=self.toggle_mute)
        game_menu.add_separator()
        game_menu.add_command(label="저장 후 종료", command=self.on_close)
        menubar.add_cascade(label="게임", menu=game_menu)
        self.config(menu=menubar)

    def _build_widgets(self):
        root = ttk.Frame(self, padding=8)
        root.grid(sticky="nsew")
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="ns")
        left.rowconfigure(1, weight=1)

        self.canvas = tk.Canvas(left, width=CANVAS_W, height=CANVAS_H, bg="#120f2e", highlightthickness=0)
        self.canvas.grid(row=0, column=0)
        self.canvas.bind("<Button-1>", self.on_map_click)
        self.canvas.bind("<Motion>", self.on_map_hover)

        log_frame = ttk.Frame(left)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, width=10, height=6, font=FONT, state="disabled", wrap="word",
                                relief="flat", padx=8, pady=6)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.tag_configure("star", foreground="#b8860b", font=FONT_BOLD)
        self.log_text.tag_configure("danger", foreground="#c0392b", font=FONT_BOLD)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=scroll.set)

        side = ttk.Frame(root, padding=(12, 0, 0, 0))
        side.grid(row=0, column=1, sticky="ns")

        head = ttk.Frame(side)
        head.pack(fill="x")
        self.day_label = ttk.Label(head, font=FONT_BOLD)
        self.day_label.pack(side="left")
        # 남은 목숨: 기절할 때마다 ♥ 하나가 ♡ 로 바뀐다
        bg = ttk.Style(self).lookup("TFrame", "background")
        self.lives_lost_label = tk.Label(head, font=("맑은 고딕", 12, "bold"), fg="#b8b8c4", bg=bg)
        self.lives_lost_label.pack(side="right")
        self.lives_label = tk.Label(head, font=("맑은 고딕", 12, "bold"), fg="#e0455a", bg=bg)
        self.lives_label.pack(side="right")
        self.loc_label = ttk.Label(side, font=FONT, wraplength=230, justify="left")
        self.loc_label.pack(anchor="w")
        self.loc_cost_label = ttk.Label(side, font=FONT_SMALL, foreground="gray")
        self.loc_cost_label.pack(anchor="w", pady=(0, 8))

        self.oxygen_bar, self.oxygen_text = self._bar(side, "산소", MAX_OXYGEN, "O2")
        self.energy_bar, self.energy_text = self._bar(side, "체력", MAX_ENERGY, "Energy")
        self.repair_bar, self.repair_text = self._bar(side, "로켓 수리", 100, "Repair")

        ttk.Label(side, text="가방", font=FONT_BOLD).pack(anchor="w", pady=(8, 0))
        self.inv_label = ttk.Label(side, font=FONT, justify="left")
        self.inv_label.pack(anchor="w")

        ttk.Separator(side).pack(fill="x", pady=8)

        move_row = ttk.Frame(side)
        move_row.pack(fill="x")
        self.dest_var = tk.StringVar()
        self.dest_box = ttk.Combobox(move_row, textvariable=self.dest_var, state="readonly", width=15)
        self.dest_box.pack(side="left")
        self.dest_box.bind("<<ComboboxSelected>>", lambda e: self._update_move_cost())
        self.move_btn = ttk.Button(move_row, text="이동", command=self.on_move)
        self.move_btn.pack(side="left", padx=4, fill="x", expand=True)
        self.move_cost_label = ttk.Label(side, font=FONT_SMALL, foreground="gray")
        self.move_cost_label.pack(anchor="w", pady=(0, 4))

        g = self.game
        self.home_btn = ttk.Button(side, command=lambda: self.act(g.move, "base"))
        self.home_btn.pack(fill="x", pady=(0, 4), ipady=3)

        grid = ttk.Frame(side)
        grid.pack(fill="x")
        grid.columnconfigure((0, 1), weight=1, uniform="actions")
        self.action_buttons = [
            ttk.Button(grid, text="탐색", command=lambda: self.act(g.explore)),
            ttk.Button(grid, text="휴식 (기지)", command=lambda: self.act(g.rest)),
            ttk.Button(grid, text="로켓 수리 (기지)", command=lambda: self.act(g.repair)),
            ttk.Button(grid, text="🚀 발사!", command=lambda: self.act(g.launch)),
        ]
        for i, btn in enumerate(self.action_buttons):     # 2열로 배치해 창 높이를 줄인다
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 2) if i % 2 == 0 else (2, 0), pady=2)

        ttk.Label(side, text="아이템 사용", font=FONT_BOLD).pack(anchor="w", pady=(8, 0))
        self.item_buttons = {}
        for item in CONSUMABLES:
            btn = ttk.Button(side, command=lambda i=item: self.act(g.use_item, i))
            btn.pack(fill="x", pady=2)
            self.item_buttons[item] = btn
            self.action_buttons.append(btn)

        bottom = ttk.Frame(side)
        bottom.pack(fill="x", pady=(8, 0))
        self.status_label = ttk.Label(bottom, font=FONT_SMALL, foreground="gray")
        self.status_label.pack(side="left")
        # 진행 중이든 엔딩 후든 언제나 누를 수 있다 (확인 → 난이도 선택 후 새로 시작)
        ttk.Button(bottom, text="🔄 새 게임", command=self.new_game).pack(side="right")
        self.sound_btn = ttk.Button(bottom, command=self.toggle_mute_button)
        self.sound_btn.pack(side="right", padx=(0, 4))
        self._update_sound_button()

    def _bar(self, parent, title, maximum, style):
        head = ttk.Frame(parent)
        head.pack(fill="x")
        ttk.Label(head, text=title, font=FONT).pack(side="left")
        value = ttk.Label(head, font=FONT_SMALL, foreground="gray")
        value.pack(side="right")
        bar = ttk.Progressbar(parent, length=230, maximum=maximum, style=f"{style}.Horizontal.TProgressbar")
        bar.pack(anchor="w", pady=(0, 4))
        return bar, value

    # ---------- 흐름 ----------
    def act(self, action, *args):
        action(*args)
        self.after_change()

    def after_change(self):
        """상태가 바뀐 뒤 항상 거치는 길: 업적 → 저장 → 소리 → 그리기 → 이벤트/엔딩."""
        g = self.game
        for aid in self.records.update_from(g.state):
            g.log(f"★ 업적 달성: {ACHIEVEMENTS[aid][0]} — {ACHIEVEMENTS[aid][1]}")
            g.sounds.append("achieve")
        self.persist()
        self.sound.play_queue(g.sounds)
        self.refresh()
        if g.state.pending_event:
            self.after(500, self.show_event_if_pending)
        elif g.state.ending and not self._ending_shown:
            self._ending_shown = True
            self.animate_launch()
        elif g.state.game_over and not self._gameover_shown:
            self._gameover_shown = True
            self.after(700, lambda: dialogs.GameOverDialog(self, g.state, self.records, self.new_game))

    def first_run(self):
        diff = dialogs.ask_difficulty(self, cancellable=False)
        if self._closed:                 # 난이도를 고르기 전에 창을 닫은 경우
            return
        self.game.state.difficulty = diff or "normal"
        self.after_change()

    def show_event_if_pending(self):
        if self._event_open or not self.game.state.pending_event:
            return
        self._event_open = True

        def chosen(index):
            self._event_open = False
            self.game.resolve_event(index)
            self.after_change()

        dialogs.EventDialog(self, self.game, chosen)

    def on_move(self):
        dest = self._selected_dest()
        if dest:
            self.act(self.game.move, dest)

    def _location_at(self, x, y):
        """지도에서 클릭/커서 위치에 있는, 이동 가능한 지역 id."""
        s = self.game.state
        if not FEET_Y - 55 <= y <= CANVAS_H or s.ending or s.game_over or s.pending_event:
            return None
        for loc_id, info in LOCATIONS.items():
            if abs(info["x"] - x) <= 45 and loc_id in s.discovered and loc_id != s.location:
                return loc_id
        return None

    def on_map_click(self, event):
        dest = self._location_at(event.x, event.y)
        if dest:
            self.act(self.game.move, dest)

    def on_map_hover(self, event):
        self.canvas.config(cursor="hand2" if self._location_at(event.x, event.y) else "")

    def _selected_dest(self):
        names = {LOCATIONS[k]["name"]: k for k in self.game.state.discovered}
        return names.get(self.dest_var.get())

    def new_game(self):
        s = self.game.state
        if not (s.ending or s.game_over) and s.total_actions > 0:
            if not messagebox.askyesno("새 게임", "지금까지의 진행 상황이 사라집니다. 새로 시작할까요?\n(기록과 업적은 남습니다)"):
                return
        diff = dialogs.ask_difficulty(self, cancellable=True)
        if diff is None:
            return
        self.game.state = GameState(difficulty=diff)
        self.game.sounds.clear()
        self.game.log(INTRO)
        self._ending_shown = False
        self._gameover_shown = False
        self.rocket_lift = 0
        self.cat_x = self._cat_target()
        self.after_change()

    def toggle_mute(self):
        """메뉴의 '소리 끄기'와 화면의 소리 버튼이 함께 쓰는 길. 설정은 records.json에 남는다."""
        self.records.muted = self.sound.muted = self.muted_var.get()
        if self.sound.muted:
            self.sound.stop()
        self._update_sound_button()
        self.persist()

    def toggle_mute_button(self):
        self.muted_var.set(not self.muted_var.get())
        self.toggle_mute()

    def _update_sound_button(self):
        self.sound_btn.config(text="🔇 소리 끔" if self.muted_var.get() else "🔊 소리 켬")

    def persist(self):
        try:
            save_manager.save_records(self.records)
            save_manager.save(self.game.state)
            self.status_label.config(text="자동 저장됨")
        except OSError as e:
            self.status_label.config(text="저장 실패!")
            messagebox.showwarning("저장 실패", f"저장하지 못했습니다: {e}")

    def on_close(self):
        self.persist()
        self._closed = True
        self.destroy()

    # ---------- 화면 갱신 ----------
    def refresh(self):
        g, s = self.game, self.game.state
        here = LOCATIONS[s.location]
        diff = DIFFICULTIES.get(s.difficulty, DIFFICULTIES["normal"])["name"]
        self.day_label.config(text=f"{s.day}일차  ·  {diff}")
        left = g.lives_left()
        self.lives_label.config(text="♥" * left)
        self.lives_lost_label.config(text="♡" * (g.difficulty["max_faints"] - left))
        self.loc_label.config(text=f"📍 {here['name']}\n{here['desc']}")
        self.loc_cost_label.config(
            text="" if s.location == "base" else f"탐색하면 산소 −{g.explore_cost()} · 체력 −15")

        self.oxygen_bar["value"] = s.oxygen
        self.oxygen_bar.config(style=("Low" if s.oxygen <= 30 else "O2") + ".Horizontal.TProgressbar")
        self.oxygen_text.config(text=f"{s.oxygen} / {MAX_OXYGEN}")
        self.energy_bar["value"] = s.energy
        self.energy_text.config(text=f"{s.energy} / {MAX_ENERGY}")
        progress = g.repair_progress()
        self.repair_bar["value"] = progress * 100
        installed = sum(min(s.installed.get(k, 0), n) for k, n in REPAIR_REQUIREMENTS.items())
        self.repair_text.config(text=f"{installed} / {sum(REPAIR_REQUIREMENTS.values())} 부품")

        lines = [f"{ITEMS[k]} × {n}" + (f"   ({g.item_effect_text(k)})" if k in CONSUMABLES else "")
                 for k, n in s.inventory.items()]
        self.inv_label.config(text="\n".join(lines) or "(비어 있음)")

        dests = [LOCATIONS[k]["name"] for k in s.discovered if k != s.location]
        self.dest_box["values"] = dests
        if self.dest_var.get() not in dests:
            self.dest_var.set(dests[0] if dests else "")
        self._update_move_cost()

        for item, btn in self.item_buttons.items():
            btn.config(text=f"{ITEMS[item]} 사용 ({s.inventory.get(item, 0)})  ·  {g.item_effect_text(item)}")
        busy = s.ending or s.game_over or bool(s.pending_event)
        for btn in (*self.action_buttons, self.move_btn):
            btn.config(state="disabled" if busy else "normal")
        if s.location == "base":
            self.home_btn.config(text="🏠 기지에 있음", state="disabled")
        else:
            self.home_btn.config(text=f"🏠 기지로 귀환  (산소 −{g.move_cost('base')})",
                                 state="disabled" if busy else "normal")
        for item, btn in self.item_buttons.items():
            if not busy and s.inventory.get(item, 0) == 0:
                btn.config(state="disabled")

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        for line in s.log:
            tag = ("star",) if "★" in line else ("danger",) if "게임오버" in line or "한 번만 더" in line else ()
            self.log_text.insert("end", line + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

        self.walk_cat()

    def _update_move_cost(self):
        dest = self._selected_dest()
        if not dest:
            self.move_cost_label.config(text="")
            return
        text = f"이동하면 산소 −{self.game.move_cost(dest)}"
        if dest == "base":
            text += " (도착하면 가득 충전)"
        self.move_cost_label.config(text=text)

    # ---------- 애니메이션 ----------
    def walk_cat(self):
        if self._walk_job:
            self.after_cancel(self._walk_job)
            self._walk_job = None
        target = self._cat_target()

        def step(frame=0):
            dx = target - self.cat_x
            if abs(dx) <= WALK_SPEED:
                self.cat_x, self.cat_hop, self._walk_job = target, 0.0, None
                self.draw_scene()
                return
            self.cat_x += WALK_SPEED if dx > 0 else -WALK_SPEED
            self.cat_hop = abs(math.sin(frame * 0.5)) * 7
            self.draw_scene()
            self._walk_job = self.after(FRAME_MS, step, frame + 1)

        step()

    def animate_launch(self):
        launched = self.game.state

        def step():
            if self.game.state is not launched:      # 발사 도중 새 게임을 눌렀으면 중단
                return
            self.rocket_lift = min(ROCKET_GONE, self.rocket_lift + 2 + self.rocket_lift * 0.06)
            self.draw_scene()
            if self.rocket_lift < ROCKET_GONE:
                self.after(FRAME_MS, step)
            else:
                dialogs.EndingDialog(self, self.game.state, self.records, self.new_game)

        self.after(300, step)

    def _cat_target(self):
        loc = self.game.state.location
        return LOCATIONS[loc]["x"] + (BASE_CAT_OFFSET if loc == "base" else 0)

    # ---------- 그리기 ----------
    def _outlined_text(self, x, y, text, size, color, bold=True):
        """배경 그림의 글자처럼 진한 테두리를 두른 글자."""
        font = ("맑은 고딕", size, "bold" if bold else "normal")
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                if dx or dy:
                    self.canvas.create_text(x + dx, y + dy, text=text, fill=OUTLINE, font=font)
        self.canvas.create_text(x, y, text=text, fill=color, font=font)

    def draw_scene(self):
        c, s = self.canvas, self.game.state
        c.delete("all")
        c.create_image(0, 0, image=self.sprites["background"], anchor="nw")

        for i, (loc_id, info) in enumerate(LOCATIONS.items()):
            known = loc_id in s.discovered
            if not known and loc_id in LOCK_POS:
                c.create_image(*LOCK_POS[loc_id], image=self.sprites[f"lock_{i}"], anchor="nw")
            if loc_id == s.location:
                color = "#ffe27a"
            else:
                color = "#f4f1ff" if known else "#b9b1d8"
            self._outlined_text(info["x"], LABEL_Y, info["name"] if known else "???", 11, color)

        self._draw_rocket(c, self.game.repair_progress())

        flying = s.ending
        companion = s.flags.get("rabbit_companion")
        if s.flags.get("rabbit_rescued") and not companion and not flying:
            c.create_image(LOCATIONS["ice_cave"]["x"] + RABBIT_OFFSET, FEET_Y, image=self.sprites["rabbit"], anchor="s")
        if not flying:
            if companion:
                # 기지에선 왼쪽에 로켓이, 달의 뒷면에선 오른쪽에 화면 끝이 있어 방향을 바꾼다
                side = 1 if s.location == "base" else -1
                c.create_image(self.cat_x + side * RABBIT_OFFSET, FEET_Y - self.cat_hop * 0.6,
                               image=self.sprites["rabbit"], anchor="s")
            c.create_image(self.cat_x, FEET_Y - self.cat_hop, image=self.sprites["cat"], anchor="s")
        elif self.rocket_lift >= ROCKET_GONE:
            title = ENDINGS[s.ending_type or "normal"][0]
            self._outlined_text(CANVAS_W // 2 - 60, 120, "귀환 성공!", 24, "#ffffff")
            self._outlined_text(CANVAS_W // 2 - 60, 158, f"엔딩 · {title}  ({s.day}일)", 12, "#ffe27a")

        if s.game_over:
            c.create_rectangle(0, 92, CANVAS_W, 178, fill="#120f2e", outline="#e0455a", width=2)
            self._outlined_text(CANVAS_W // 2, 122, "GAME OVER", 26, "#ff5c6c")
            self._outlined_text(CANVAS_W // 2, 156, f"나비는 달의 고양이가 되었다…  ({s.day}일차)", 11, "#f4f1ff")

    def _draw_rocket(self, c, progress):
        lift = self.rocket_lift
        if lift >= ROCKET_GONE:
            return
        x, y = ROCKET_POS
        w, h = ROCKET_SIZE
        cx, bottom = x + w // 2, y + h - lift
        if lift > 0:
            flicker = random.randint(0, 14)
            c.create_polygon(cx - 12, bottom - 6, cx, bottom + 30 + flicker, cx + 12, bottom - 6,
                             fill="#ffb347", outline="")
            c.create_polygon(cx - 6, bottom - 6, cx, bottom + 16 + flicker // 2, cx + 6, bottom - 6,
                             fill="#fff3b0", outline="")
        c.create_image(x, y - lift, image=self.sprites["rocket"], anchor="nw")
        if lift == 0:
            self._outlined_text(LOCATIONS["base"]["x"], PERCENT_Y, f"{progress:.0%}", 12,
                                "#7dff9b" if progress >= 1 else "#ffffff")

"""게임 규칙. tkinter를 전혀 모르므로 UI 없이 테스트할 수 있다.

모든 행동은 GameState만 바꾸고, 결과는 state.log에 기록한다.
효과음 이름은 self.sounds에 쌓아 두면 UI가 꺼내서 재생한다(저장하지 않음).
"""
import random

from .config import (
    CONSUMABLES, DIFFICULTIES, DISCOVER_CHANCE, EXPLORE_ENERGY_COST, FAINT_ENERGY,
    ITEMS, LOCATIONS, LOG_LIMIT, MAX_ENERGY, MAX_OXYGEN, REPAIR_ENERGY_COST,
    REPAIR_REQUIREMENTS,
)
from .events import ENDINGS, EVENTS
from .state import GameState

STAT_NAMES = {"oxygen": "산소", "energy": "체력"}

INTRO ="쿵! 우주 고양이 '나비'의 로켓이 달에 불시착했다. 부품을 모아 지구로 돌아가자."


class Game:
    def __init__(self, state: GameState, rng: random.Random | None = None):
        self.state = state
        self.rng = rng or random.Random()
        self.sounds: list[str] = []

    # ---------- 공통 ----------
    def log(self, msg: str) -> None:
        self.state.log.append(f"[{self.state.day}일차] {msg}")
        del self.state.log[:-LOG_LIMIT]

    @property
    def here(self) -> dict:
        return LOCATIONS[self.state.location]

    @property
    def difficulty(self) -> dict:
        return DIFFICULTIES.get(self.state.difficulty, DIFFICULTIES["normal"])

    def oxygen_cost(self, base: int) -> int:
        return round(base * self.difficulty["oxygen_mult"])

    def move_cost(self, loc_id: str) -> int:
        if loc_id == self.state.location:
            return 0
        # 기지로 돌아갈 때는 현재 지역의 거리만큼 산소를 쓴다
        base = self.here["travel_cost"] if loc_id == "base" else LOCATIONS[loc_id]["travel_cost"]
        return self.oxygen_cost(base)

    def explore_cost(self) -> int:
        return self.oxygen_cost(self.here["explore_cost"])

    def repair_progress(self) -> float:
        need = sum(REPAIR_REQUIREMENTS.values())
        done = sum(min(self.state.installed.get(k, 0), n) for k, n in REPAIR_REQUIREMENTS.items())
        return done / need

    def _blocked(self) -> bool:
        if self.state.ending:
            self.log("나비는 이미 지구에 돌아왔다. 메뉴에서 새 게임을 시작할 수 있다.")
            return True
        if self.state.game_over:
            self.log("게임오버. '새 게임'으로 다시 도전하자.")
            return True
        if self.state.pending_event:
            self.log("먼저 눈앞의 일부터 해결하자.")
            return True
        return False

    def lives_left(self) -> int:
        """앞으로 기절해도 버틸 수 있는 횟수 + 1 (화면의 ♥ 개수). 0이면 게임오버."""
        return max(0, self.difficulty["max_faints"] - self.state.faint_count)

    def _spend_oxygen(self, amount: int) -> bool:
        """산소를 쓰고, 바닥나면 기절 처리. 기절했으면 True."""
        s = self.state
        s.oxygen -= amount
        if s.oxygen > 0:
            return False
        s.faint_count += 1
        if self.lives_left() == 0:
            s.oxygen = 0
            s.game_over = True
            self.log("산소가 바닥나 쓰러졌다… 나비는 다시 일어나지 못했다. (게임오버)")
            self.sounds.append("gameover")
            return True
        s.location = "base"
        s.oxygen = MAX_OXYGEN
        s.energy = FAINT_ENERGY
        s.day += 1
        lost = ""
        if s.inventory:
            item = self.rng.choice(sorted(s.inventory))
            self._take(item)
            lost = f" 정신을 잃은 사이 {ITEMS[item]} 하나를 잃어버렸다."
        self.log("산소가 바닥나 기절했다... 눈을 떠 보니 포드 안이다." + lost)
        left = self.lives_left()
        self.log(f"남은 목숨 ♥ {left}" + ("  — 한 번만 더 쓰러지면 끝이다! 산소를 조심하자." if left == 1 else ""))
        self.sounds.append("faint")
        return True

    def _give(self, item: str, n: int = 1) -> None:
        self.state.inventory[item] = self.state.inventory.get(item, 0) + n

    def _take(self, item: str, n: int = 1) -> None:
        left = self.state.inventory.get(item, 0) - n
        if left > 0:
            self.state.inventory[item] = left
        else:
            self.state.inventory.pop(item, None)

    def _tick(self) -> None:
        self.state.total_actions += 1

    # ---------- 행동 ----------
    def move(self, loc_id: str) -> None:
        s = self.state
        if self._blocked():
            return
        if loc_id not in s.discovered:
            self.log("아직 가 본 적 없는 곳이다.")
            return
        if loc_id == s.location:
            self.log("이미 여기 있다.")
            return
        self._tick()
        if self._spend_oxygen(self.move_cost(loc_id)):
            return
        s.location = loc_id
        self.sounds.append("step")
        if loc_id == "base":
            s.oxygen = MAX_OXYGEN
            self.log("기지에 돌아와 산소를 가득 채웠다.")
        else:
            self.log(f"{self.here['name']}에 도착했다. {self.here['desc']}")
            self._queue_event("arrive")

    def explore(self) -> None:
        s = self.state
        if self._blocked():
            return
        if s.location == "base":
            self.log("기지 주변은 이미 샅샅이 뒤졌다. 다른 곳으로 가 보자.")
            return
        if s.energy < EXPLORE_ENERGY_COST:
            self.log("너무 지쳤다... 먹을 것을 먹거나 기지에서 쉬자.")
            return
        self._tick()
        s.energy -= EXPLORE_ENERGY_COST
        if self._spend_oxygen(self.explore_cost()):
            return

        loot = self.here["loot"]
        weights = [w * self.difficulty["nothing_mult"] if k == "nothing" else w for k, w in loot.items()]
        item = self.rng.choices(list(loot), weights=weights)[0]
        if item == "nothing":
            self.log("열심히 뒤졌지만 먼지만 잔뜩 묻었다.")
            self.sounds.append("fail")
        else:
            self._give(item)
            self.log(f"{ITEMS[item]}을(를) 찾았다!")
            self.sounds.append("find")

        for loc_id, info in LOCATIONS.items():
            if info["found_in"] == s.location and loc_id not in s.discovered:
                if self.rng.random() < DISCOVER_CHANCE:
                    s.discovered.append(loc_id)
                    self.log(f"멀리 새로운 장소가 보인다: {info['name']}")

    def rest(self) -> None:
        s = self.state
        if self._blocked():
            return
        if s.location != "base":
            self.log("밖에서는 잘 수 없다. '기지로 귀환' 버튼으로 먼저 돌아가자.")
            return
        self._tick()
        s.day += 1
        s.energy = MAX_ENERGY
        s.oxygen = MAX_OXYGEN
        self.log("포드 안에서 동그랗게 몸을 말고 푹 잤다.")
        self._queue_event("rest")

    def repair(self) -> None:
        s = self.state
        if self._blocked():
            return
        if s.location != "base":
            self.log("로켓은 기지에 있다. '기지로 귀환' 버튼으로 먼저 돌아가자.")
            return
        if s.energy < REPAIR_ENERGY_COST:
            self.log("수리할 기운이 없다.")
            return
        installed = []
        for item, need in REPAIR_REQUIREMENTS.items():
            while s.installed.get(item, 0) < need and s.inventory.get(item, 0) > 0:
                self._take(item)
                s.installed[item] = s.installed.get(item, 0) + 1
                installed.append(ITEMS[item])
        if not installed:
            self.log("장착할 부품이 없다. 남은 부품: " + self.missing_parts_text())
            return
        self._tick()
        s.energy -= REPAIR_ENERGY_COST
        self.log(f"{', '.join(installed)} 장착 완료! 수리 {self.repair_progress():.0%}")
        self.sounds.append("repair")

    def use_item(self, item: str) -> None:
        s = self.state
        if self._blocked():
            return
        if s.inventory.get(item, 0) <= 0:
            self.log(f"{ITEMS[item]}이(가) 없다.")
            return
        stat, amount = CONSUMABLES[item]
        cap = MAX_ENERGY if stat == "energy" else MAX_OXYGEN
        before = getattr(s, stat)
        if before >= cap:
            subject = "산소가" if stat == "oxygen" else "체력이"
            self.log(f"{subject} 이미 가득 차 있다. {ITEMS[item]}은(는) 아껴 두자.")
            return
        self._tick()
        self._take(item)
        setattr(s, stat, min(cap, before + amount))
        flavor = "숨이 편해졌다." if stat == "oxygen" else "기운이 난다."
        self.log(f"{ITEMS[item]} 사용! {self.item_effect_text(item)} ({before} → {getattr(s, stat)}) {flavor}")

    def item_effect_text(self, item: str) -> str:
        stat, amount = CONSUMABLES[item]
        return f"{STAT_NAMES[stat]} +{amount}"

    def launch(self) -> None:
        s = self.state
        if self._blocked():
            return
        if s.location != "base":
            self.log("로켓은 기지에 있다. '기지로 귀환' 버튼으로 먼저 돌아가자.")
            return
        if self.repair_progress() < 1:
            self.log("아직 날 수 없다. 남은 부품: " + self.missing_parts_text())
            return
        self._tick()
        s.ending = True
        s.ending_type = "rabbit" if s.flags.get("rabbit_companion") else "normal"
        self.log("3, 2, 1... 발사! " + self.ending_text())
        self.sounds.append("launch")

    def ending_text(self) -> str:
        return ENDINGS[self.state.ending_type or "normal"][1].format(day=self.state.day)

    def missing_parts_text(self) -> str:
        parts = [
            f"{ITEMS[k]} {n - self.state.installed.get(k, 0)}"
            for k, n in REPAIR_REQUIREMENTS.items()
            if self.state.installed.get(k, 0) < n
        ]
        return ", ".join(parts) or "없음"

    # ---------- 이벤트 ----------
    def _queue_event(self, trigger: str) -> None:
        s = self.state
        if s.pending_event:
            return
        for eid, ev in EVENTS.items():
            if ev["trigger"] != trigger:
                continue
            if ev.get("location") and ev["location"] != s.location:
                continue
            if ev.get("once", True) and s.flags.get(f"seen:{eid}"):
                continue
            if not all(s.flags.get(f) for f in ev.get("need_flags", [])):
                continue
            if any(s.flags.get(f) for f in ev.get("block_flags", [])):
                continue
            if self.rng.random() >= ev.get("chance", 1.0):
                continue
            s.pending_event = eid
            self.sounds.append("event")
            return

    def current_event(self) -> dict | None:
        return EVENTS.get(self.state.pending_event) if self.state.pending_event else None

    def choice_available(self, choice: dict) -> bool:
        return all(self.state.flags.get(f) for f in choice.get("need_flags", []))

    def choice_cost_text(self, choice: dict) -> str:
        parts = []
        if choice.get("oxygen", 0) < 0:
            parts.append(f"산소 −{self.oxygen_cost(-choice['oxygen'])}")
        if choice.get("energy", 0) < 0:
            parts.append(f"체력 −{-choice['energy']}")
        return " · ".join(parts)

    def resolve_event(self, index: int) -> None:
        s = self.state
        ev = self.current_event()
        if ev is None or not 0 <= index < len(ev["choices"]):
            return
        choice = ev["choices"][index]
        if not self.choice_available(choice):
            return
        s.flags[f"seen:{s.pending_event}"] = True
        s.pending_event = None
        self._tick()

        for item, n in choice.get("items", {}).items():
            if n > 0:
                self._give(item, n)
            else:
                self._take(item, -n)
        for flag in choice.get("flags", []):
            s.flags[flag] = True
        for loc in choice.get("discover", []):
            if loc not in s.discovered:
                s.discovered.append(loc)
        if "energy" in choice:
            s.energy = max(0, min(MAX_ENERGY, s.energy + choice["energy"]))
        self.log(choice["result"])
        if choice.get("items"):
            self.sounds.append("find")

        oxygen = choice.get("oxygen", 0)
        if oxygen < 0:
            self._spend_oxygen(self.oxygen_cost(-oxygen))
        elif oxygen > 0:
            s.oxygen = min(MAX_OXYGEN, s.oxygen + oxygen)

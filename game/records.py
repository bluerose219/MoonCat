"""새 게임을 시작해도 남는 기록: 클리어 횟수, 최단 귀환, 업적, 소리 설정."""
from dataclasses import asdict, dataclass, field, fields

from .config import LOCATIONS, SPEEDRUN_DAYS
from .state import GameState

ACHIEVEMENTS = {
    "first_clear": ("첫 귀환", "지구로 무사히 돌아왔다"),
    "speedrun": ("총알 고양이", f"{SPEEDRUN_DAYS}일 이내에 귀환"),
    "no_faint": ("숨 참기 달인", "한 번도 기절하지 않고 귀환"),
    "hard_clear": ("강철 발바닥", "어려움 난이도로 귀환"),
    "rabbit": ("달토끼의 친구", "달토끼와 함께 귀환"),
    "explorer": ("달 탐험가", "모든 지역 발견"),
}


@dataclass
class Records:
    clears: int = 0
    game_overs: int = 0
    best_days: int | None = None
    achievements: list[str] = field(default_factory=list)
    muted: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Records":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def update_from(self, state: GameState) -> list[str]:
        """현재 게임 상태를 반영하고, 새로 딴 업적 id 목록을 돌려준다."""
        earned = []

        def grant(aid: str) -> None:
            if aid not in self.achievements:
                self.achievements.append(aid)
                earned.append(aid)

        if set(LOCATIONS) <= set(state.discovered):
            grant("explorer")

        if state.game_over and not state.flags.get("recorded"):
            state.flags["recorded"] = True
            self.game_overs += 1

        # 같은 클리어를 두 번 세지 않도록 게임 상태에 표시해 둔다
        if state.ending and not state.flags.get("recorded"):
            state.flags["recorded"] = True
            self.clears += 1
            if self.best_days is None or state.day < self.best_days:
                self.best_days = state.day
            grant("first_clear")
            if state.day <= SPEEDRUN_DAYS:
                grant("speedrun")
            if state.faint_count == 0:
                grant("no_faint")
            if state.difficulty == "hard":
                grant("hard_clear")
            if state.ending_type == "rabbit":
                grant("rabbit")
        return earned

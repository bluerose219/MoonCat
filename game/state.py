"""게임의 '모든' 진행 상황을 담는 데이터.

규칙: 재시작 후에도 남아야 하는 값은 반드시 GameState 필드로 둔다.
UI 위젯이나 Game 객체에만 들고 있는 값은 저장되지 않는다.
(새 게임을 해도 남아야 하는 기록·업적·설정은 records.py의 Records에 둔다.)
"""
from dataclasses import asdict, dataclass, field, fields

from .config import MAX_ENERGY, MAX_OXYGEN, SAVE_VERSION, START_LOCATIONS


@dataclass
class GameState:
    version: int = SAVE_VERSION
    difficulty: str = "normal"
    day: int = 1
    location: str = "base"
    oxygen: int = MAX_OXYGEN
    energy: int = MAX_ENERGY
    inventory: dict[str, int] = field(default_factory=dict)
    installed: dict[str, int] = field(default_factory=dict)   # 로켓에 장착한 부품
    discovered: list[str] = field(default_factory=lambda: list(START_LOCATIONS))
    flags: dict[str, bool] = field(default_factory=dict)       # 스토리 진행/본 이벤트
    pending_event: str | None = None                           # 선택을 기다리는 이벤트
    log: list[str] = field(default_factory=list)
    total_actions: int = 0
    faint_count: int = 0
    ending: bool = False
    ending_type: str = ""
    game_over: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        data = migrate(data)
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


def migrate(data: dict) -> dict:
    """구버전 세이브를 현재 버전으로 끌어올린다.

    필드를 바꿀 때 SAVE_VERSION을 올리고 여기에 변환 단계를 추가하면
    예전 세이브 파일도 계속 열린다.
    """
    version = data.get("version", 1)
    if version < 2:
        # v2: 난이도·이벤트·엔딩 종류 추가. v1 세이브는 보통 난이도, 기본 엔딩으로 본다.
        data.setdefault("difficulty", "normal")
        if data.get("ending"):
            data.setdefault("ending_type", "normal")
        version = 2
    if version < 3:
        # v3: 기절 횟수 제한(게임오버) 추가. 기존 세이브는 아직 게임오버가 아니다.
        data.setdefault("game_over", False)
        version = 3
    data["version"] = version
    return data

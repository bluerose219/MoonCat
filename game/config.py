"""게임 밸런스/콘텐츠 상수. 숫자 조정이나 지역·아이템 추가는 여기서만 하면 된다."""

SAVE_VERSION = 3

MAX_OXYGEN = 100
MAX_ENERGY = 100
EXPLORE_ENERGY_COST = 15
REPAIR_ENERGY_COST = 10
FAINT_ENERGY = 30          # 산소 고갈로 기절했다 깨어났을 때 체력
DISCOVER_CHANCE = 0.35     # 탐색 시 인접한 새 지역을 발견할 확률
LOG_LIMIT = 80             # 저장 파일에 남길 로그 줄 수
SPEEDRUN_DAYS = 10         # '총알 고양이' 업적 기준

ITEMS = {
    "hull_plate": "선체 판",
    "engine_part": "엔진 부품",
    "fuel_cell": "연료 셀",
    "antenna": "통신 안테나",
    "fish_can": "생선 통조림",
    "oxygen_tank": "휴대 산소통",
    "rice_cake": "달토끼 떡",
}

# 로켓 수리에 필요한 부품과 개수
REPAIR_REQUIREMENTS = {
    "hull_plate": 3,
    "engine_part": 2,
    "fuel_cell": 3,
    "antenna": 1,
}

# 소모품 효과: (스탯, 회복량)
CONSUMABLES = {
    "fish_can": ("energy", 40),
    "oxygen_tank": ("oxygen", 40),
    "rice_cake": ("energy", 70),
}

# oxygen_mult: 산소 소모 배율, nothing_mult: 탐색 허탕 확률 배율
# max_faints: 이 횟수만큼 기절하면 게임오버 (화면의 ♥ 개수)
DIFFICULTIES = {
    "easy": {"name": "쉬움", "desc": "산소를 적게 쓰고 허탕이 적다",
             "oxygen_mult": 0.7, "nothing_mult": 0.6, "max_faints": 5},
    "normal": {"name": "보통", "desc": "기본 규칙",
               "oxygen_mult": 1.0, "nothing_mult": 1.0, "max_faints": 3},
    "hard": {"name": "어려움", "desc": "산소를 많이 쓰고 허탕이 잦다",
             "oxygen_mult": 1.3, "nothing_mult": 1.5, "max_faints": 2},
}

# travel_cost: 이동 시 산소 소모, explore_cost: 탐색 시 산소 소모
# found_in: 이 지역을 탐색하다가 발견할 수 있는 지역
# x: 배경 그림(game/assets/background.png)에서 받침대 중심의 가로 위치
# loot: 탐색 시 얻는 아이템 가중치 ("nothing" = 허탕)
LOCATIONS = {
    "base": {
        "name": "불시착 지점",
        "desc": "부서진 로켓과 산소 포드가 있다. 산소가 자동으로 보충된다.",
        "travel_cost": 0, "explore_cost": 0, "found_in": None, "x": 69,
        "loot": {},
    },
    "crater": {
        "name": "고요의 크레이터",
        "desc": "로켓에서 떨어져 나간 파편이 흩어져 있다.",
        "travel_cost": 10, "explore_cost": 10, "found_in": None, "x": 242,
        "loot": {"hull_plate": 35, "fish_can": 20, "oxygen_tank": 10, "nothing": 35},
    },
    "ice_cave": {
        "name": "얼음 동굴",
        "desc": "차갑게 빛나는 얼음 속에 연료 셀이 얼어붙어 있다.",
        "travel_cost": 15, "explore_cost": 15, "found_in": "crater", "x": 397,
        "loot": {"fuel_cell": 35, "oxygen_tank": 20, "nothing": 45},
    },
    "probe": {
        "name": "버려진 탐사선",
        "desc": "오래전 인류가 남긴 탐사선. 쓸 만한 부품이 남아 있을지도.",
        "travel_cost": 20, "explore_cost": 15, "found_in": "ice_cave", "x": 543,
        "loot": {"engine_part": 30, "hull_plate": 20, "antenna": 10, "fish_can": 10, "nothing": 30},
    },
    "far_side": {
        "name": "달의 뒷면",
        "desc": "지구가 보이지 않는 어둠의 땅. 위험하지만 보상도 크다.",
        "travel_cost": 30, "explore_cost": 20, "found_in": "probe", "x": 689,
        "loot": {"antenna": 25, "engine_part": 20, "fuel_cell": 20, "nothing": 35},
    },
}

START_LOCATIONS = ["base", "crater"]

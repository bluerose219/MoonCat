"""이야기 이벤트와 엔딩. 새 이벤트는 EVENTS에 항목만 추가하면 된다.

이벤트 키
  trigger     "arrive"(지역 도착) | "rest"(기지에서 휴식 후)
  location    arrive 이벤트가 일어나는 지역
  once        False면 반복 가능 (기본 True)
  chance      발생 확률 (기본 1.0)
  need_flags  이 플래그가 모두 있어야 발생
  block_flags 이 플래그 중 하나라도 있으면 발생 안 함

선택지 키
  label, result   버튼 문구, 고른 뒤 로그에 남는 문장
  oxygen, energy  증감량 (산소 감소는 난이도 배율 적용)
  items           {아이템: 개수} (음수면 소모)
  flags           켜 줄 플래그 목록
  discover        발견 처리할 지역 목록
  need_flags      이 플래그가 있어야 고를 수 있음 / lock_hint: 잠겼을 때 보여 줄 힌트
"""

EVENTS = {
    "crater_glint": {
        "trigger": "arrive", "location": "crater",
        "title": "크레이터 바닥의 반짝임",
        "text": "크레이터 깊은 곳에서 무언가 반짝인다. 로켓에서 떨어져 나간 조각 같다. 하지만 경사가 꽤 가파르다.",
        "choices": [
            {"label": "조심조심 내려가 본다", "oxygen": -10, "items": {"hull_plate": 1},
             "result": "미끄러질 뻔했지만 선체 판을 건져 올렸다!"},
            {"label": "위험해 보인다. 다음에 오자",
             "result": "나비는 꼬리를 한 번 흔들고 돌아섰다."},
        ],
    },
    "frozen_rabbit": {
        "trigger": "arrive", "location": "ice_cave",
        "title": "얼음 속의 달토끼",
        "text": "동굴 안쪽 얼음 기둥 속에 하얀 토끼가 갇혀 있다. 긴 귀가 살짝 움직인다. 아직 살아 있다!",
        "choices": [
            {"label": "발톱으로 얼음을 긁어낸다", "energy": -25, "flags": ["rabbit_rescued"],
             "result": "한참을 긁자 얼음이 깨지고 달토끼가 튀어나왔다. 토끼는 꾸벅 인사하고 깡충깡충 사라졌다."},
            {"label": "지금은 내 코가 석 자다",
             "result": "나비는 미안한 마음으로 지나갔다."},
        ],
    },
    "probe_diary": {
        "trigger": "arrive", "location": "probe",
        "title": "탐사선의 일기",
        "text": "조종석에 먼지 쌓인 수첩이 놓여 있다. 옆에는 반쯤 빠진 엔진 부품도 보인다.",
        "choices": [
            {"label": "수첩을 읽는다", "discover": ["far_side"], "flags": ["diary_read"],
             "result": "'달의 뒷면에 통신 장비를 두고 왔다…' 지도에 달의 뒷면이 표시됐다!"},
            {"label": "엔진 부품부터 챙긴다", "energy": -10, "items": {"engine_part": 1},
             "result": "낑낑대며 엔진 부품을 뽑아냈다."},
        ],
    },
    "dark_signal": {
        "trigger": "arrive", "location": "far_side",
        "title": "어둠 속의 신호",
        "text": "칠흑 같은 어둠 저편에서 삐- 삐- 신호음이 들린다. 통신 안테나일지도 모른다.",
        "choices": [
            {"label": "신호를 따라 어둠 속으로", "oxygen": -25, "items": {"antenna": 1},
             "result": "숨이 가빠질 무렵 안테나를 찾았다!"},
            {"label": "달토끼를 부른다", "need_flags": ["rabbit_rescued"], "items": {"antenna": 1},
             "lock_hint": "누군가 길을 안다면…",
             "result": "어디선가 달토끼가 나타나 지름길로 안내해 주었다. 안테나를 손쉽게 찾았다!"},
            {"label": "너무 어둡다. 돌아선다",
             "result": "나비는 귀를 납작하게 하고 물러났다."},
        ],
    },
    "rabbit_visit": {
        "trigger": "rest", "need_flags": ["rabbit_rescued"],
        "title": "한밤의 손님",
        "text": "포드 문을 똑똑 두드리는 소리. 얼음 동굴에서 구해 준 달토끼가 떡을 한 아름 들고 찾아왔다.",
        "choices": [
            {"label": "떡을 받고, 지구에 같이 가자고 한다", "flags": ["rabbit_companion"], "items": {"rice_cake": 2},
             "result": "달토끼가 귀를 쫑긋 세우더니 고개를 끄덕였다. 든든한 동료가 생겼다!"},
            {"label": "떡만 고맙게 받는다", "items": {"rice_cake": 3},
             "result": "달토끼는 앞발을 흔들고 돌아갔다."},
        ],
    },
    "meteor_shower": {
        "trigger": "rest", "once": False, "chance": 0.25,
        "title": "유성우",
        "text": "밤하늘에서 작은 운석들이 쏟아진다. 포드 지붕에 후두둑 부딪히는 소리가 난다.",
        "choices": [
            {"label": "포드 안에 꼭 숨는다",
             "result": "소리가 멎을 때까지 동그랗게 웅크렸다."},
            {"label": "떨어진 운석 조각을 주우러 나간다", "energy": -20, "items": {"hull_plate": 1},
             "result": "뜨끈한 운석 조각을 펴서 선체 판으로 쓸 수 있게 만들었다!"},
        ],
    },
    "earth_signal": {
        "trigger": "rest", "once": False, "chance": 0.2,
        "title": "지구에서 온 목소리",
        "text": "통신기의 지직거리는 소리 사이로 익숙한 목소리가 들린다. '나비야~ 밥 먹자~'",
        "choices": [
            {"label": "야옹! 하고 대답한다", "energy": 20,
             "result": "힘이 솟는다. 꼭 돌아가야지!"},
        ],
    },
}

GAME_OVER = ("달의 고양이",
             "나비는 차가운 달 표면에 쓰러져 다시 일어나지 못했다… 저 멀리 지구가 푸르게 빛나고 있었다.")

ENDINGS = {
    "normal": ("집으로",
               "나비는 {day}일 만에 지구로 돌아왔다. 현관 앞에는 따뜻한 밥그릇이 기다리고 있었다."),
    "rabbit": ("달토끼와 함께",
               "나비와 달토끼는 {day}일 만에 함께 지구에 내렸다. 그날 밤, 둘은 마당에서 보름달을 올려다보았다."),
}

"""art/moon_background.png 원본 그림을 게임용 그림 파일로 가공한다. (개발용, Pillow·numpy 필요)

원본에는 로켓·글자·자물쇠가 그려져 있어서, 게임 상황에 맞게 바뀌도록 따로 떼어 낸다.
  game/assets/background.png   글자·자물쇠·로켓을 지운 배경 (캔버스 크기)
  game/assets/rocket.png       떼어 낸 로켓 (투명 배경) → 발사 애니메이션용
  game/assets/lock_N.png       각 지역 받침대의 자물쇠 → 아직 발견 못 한 지역에만 표시
게임 실행 자체는 tkinter만으로 PNG를 읽으므로 Pillow가 필요 없다.

사용법: python tools/make_assets.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art" / "moon_background.png"
OUT = ROOT / "game" / "assets"
CANVAS_W = 760

# ---- 원본(1926×816) 좌표 ----
LABEL_BOXES = [                     # 지울 글자들
    (136, 621, 211, 666),           # "0%"
    (64, 674, 294, 734),            # 불시착 지점
    (478, 674, 738, 730),           # 고요의 크레이터
    (962, 674, 1048, 728),          # ???
    (1332, 674, 1418, 728),
    (1707, 674, 1793, 728),
]
LOCK_CENTERS = [(613, 586), (1005, 586), (1375, 586), (1745, 586)]
LOCK_HALF = (20, 28)                # 자물쇠 반폭/반높이
ROCKET_POLY = [
    (161, 288), (174, 288), (176, 312), (189, 323), (201, 347), (211, 368), (215, 380),
    (218, 458), (224, 462), (238, 480), (249, 497), (249, 560), (236, 562), (222, 549),
    (204, 538), (202, 574), (136, 574), (134, 538), (117, 549), (103, 562), (85, 560),
    (85, 497), (96, 480), (109, 462), (117, 458), (118, 380), (124, 368), (134, 347),
    (147, 323), (158, 312),
]


def inpaint(arr: np.ndarray, mask: np.ndarray, iters: int = 600) -> None:
    """mask 영역을 주변 색으로 부드럽게 메운다(라플라스 확산)."""
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min() - 2, ys.max() + 3, xs.min() - 2, xs.max() + 3
    sub = arr[y0:y1, x0:x1].astype(np.float32)
    m = mask[y0:y1, x0:x1]
    sub[m] = sub[~m].mean(axis=0)
    for _ in range(iters):
        avg = (np.roll(sub, 1, 0) + np.roll(sub, -1, 0) + np.roll(sub, 1, 1) + np.roll(sub, -1, 1)) / 4
        sub[m] = avg[m]
    # 주변 질감과 어울리도록 살짝 잡티를 섞는다
    rng = np.random.default_rng(7)
    sub[m] += rng.normal(0, 4, size=(m.sum(), 3))
    arr[y0:y1, x0:x1] = np.clip(sub, 0, 255).astype(np.uint8)


def box_mask(shape, box) -> np.ndarray:
    m = np.zeros(shape[:2], bool)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = True
    return m


def rocket_mask(size) -> np.ndarray:
    img = Image.new("L", size, 0)
    ImageDraw.Draw(img).polygon(ROCKET_POLY, fill=255)
    return np.array(img) > 0


def main() -> None:
    src = Image.open(SRC).convert("RGB")
    orig = np.array(src)
    clean = orig.copy()
    scale = CANVAS_W / src.width
    size = (CANVAS_W, round(src.height * scale))

    # 1) 로켓 떼어 내기: 원본 픽셀 + 다각형 마스크 (받침대 불빛은 제외)
    rmask = rocket_mask(src.size)
    r, g, b = (orig[..., i].astype(int) for i in range(3))
    glow = (r > 200) & (g > 120) & (b < 170)
    glow[:530] = False
    alpha = (rmask & ~glow).astype(np.uint8) * 255
    rocket = np.dstack([orig, alpha])
    ys, xs = np.nonzero(rmask)
    rbox = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)

    # 2) 로켓 자리 메우기: 뾰족한 끝은 옆 하늘을 복사하고, 나머지는 주변 구름·땅 색으로 부드럽게 메움
    fill = np.array(Image.fromarray(rmask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))) > 0
    for y, x in zip(*np.nonzero(fill)):
        if y < 335:
            clean[y, x] = orig[y, x - 70]
    body = fill.copy()
    body[:335] = False
    inpaint(clean, body, iters=3000)

    # 3) 글자와 자물쇠 지우기
    for box in LABEL_BOXES:
        inpaint(clean, box_mask(orig.shape, box))
    lock_boxes = []
    for cx, cy in LOCK_CENTERS:
        hw, hh = LOCK_HALF
        box = (cx - hw, cy - hh, cx + hw, cy + hh)
        lock_boxes.append(box)
        inpaint(clean, box_mask(orig.shape, box))

    # 4) 캔버스 크기로 줄여서 저장
    OUT.mkdir(parents=True, exist_ok=True)
    bg = Image.fromarray(clean).resize(size, Image.LANCZOS)
    bg.save(OUT / "background.png")

    # 자물쇠는 '글자만 지운 원본'을 같은 크기로 줄인 뒤 같은 칸을 잘라 낸다 → 배경과 이음새 없음
    with_locks = clean.copy()
    for box in lock_boxes:
        x0, y0, x1, y1 = box
        with_locks[y0:y1, x0:x1] = orig[y0:y1, x0:x1]
    with_locks_small = Image.fromarray(with_locks).resize(size, Image.LANCZOS)
    for i, (x0, y0, x1, y1) in enumerate(lock_boxes, start=1):
        sbox = (int(x0 * scale) - 2, int(y0 * scale) - 2, int(x1 * scale) + 3, int(y1 * scale) + 3)
        with_locks_small.crop(sbox).save(OUT / f"lock_{i}.png")
        print(f"lock_{i}: 왼쪽 위 {sbox[:2]}")

    rocket_img = Image.fromarray(rocket, "RGBA").crop(rbox)
    rw, rh = rocket_img.size
    rocket_small = rocket_img.convert("RGBa").resize((round(rw * scale), round(rh * scale)), Image.LANCZOS).convert("RGBA")
    rocket_small.save(OUT / "rocket.png")
    print(f"canvas {size}, rocket 왼쪽 위 {(round(rbox[0] * scale), round(rbox[1] * scale))} 크기 {rocket_small.size}")
    print(f"pads x: {[round(x * scale) for x in (175,) + tuple(c[0] for c in LOCK_CENTERS)]}, y: {round(586 * scale)}")


# (원본, 결과 파일, 게임 화면에서의 키 px)
CHARACTERS = [
    ("cat_astronaut.png", "cat.png", 62),
    ("rabbit_astronaut.png", "rabbit.png", 56),
]


def make_character(src_name: str, out_name: str, height: int) -> None:
    """흰 배경을 투명하게 만들고 게임 크기로 줄인다.

    우주복도 흰색이라 색으로 지우면 안 되고, 그림 가장자리에서부터 이어진 흰 영역만 지운다.
    (검은 윤곽선이 막아 주므로 우주복 안쪽은 남는다)
    """
    img = Image.open(ROOT / "art" / src_name).convert("RGB")
    key = (255, 0, 255)
    w, h = img.size
    seeds = [(x, y) for x in range(0, w, 50) for y in (0, h - 1)] + [(x, y) for y in range(0, h, 50) for x in (0, w - 1)]
    for seed in seeds:
        if img.getpixel(seed) != key:
            ImageDraw.floodfill(img, seed, key, thresh=40)
    arr = np.array(img)
    alpha = np.where((arr == key).all(axis=2), 0, 255).astype(np.uint8)
    # 윤곽선 바깥의 흐릿한 회색 테두리도 걷어 낸다
    alpha = np.array(Image.fromarray(alpha).filter(ImageFilter.MinFilter(3)))
    sprite = Image.fromarray(np.dstack([arr, alpha]), "RGBA")
    sprite = sprite.crop(sprite.getbbox())
    sw, sh = sprite.size
    small = sprite.convert("RGBa").resize((round(sw * height / sh), height), Image.LANCZOS).convert("RGBA")
    small.save(OUT / out_name)
    print(f"{out_name} {small.size}")


if __name__ == "__main__":
    main()
    for character in CHARACTERS:
        make_character(*character)

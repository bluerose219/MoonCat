"""로컬 JSON 파일로 저장/불러오기.

- 임시 파일에 먼저 쓰고 교체(os.replace) → 저장 중 꺼져도 세이브가 깨지지 않음
- 직전 파일을 .bak 으로 보관 → 본 파일이 손상되면 백업에서 복구
- OneDrive 동기화가 파일을 잠시 잡고 있을 수 있어 교체를 몇 번 재시도
- 실행 파일(PyInstaller)로 배포하면 %APPDATA%\\MoonCat 에 저장
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

from .records import Records
from .state import GameState


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.environ.get("APPDATA", Path.home())) / "MoonCat"
    return Path(__file__).resolve().parent.parent / "saves"


SAVE_DIR = _app_dir()
SAVE_FILE = SAVE_DIR / "savegame.json"
BACKUP_FILE = SAVE_DIR / "savegame.bak.json"
RECORDS_FILE = SAVE_DIR / "records.json"
RECORDS_BACKUP = SAVE_DIR / "records.bak.json"


def _write(path: Path, backup: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())

    if path.exists():
        shutil.copy2(path, backup)

    for attempt in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.1)


def _read(path: Path, backup: Path, parse):
    """본 파일 → 백업 순서로 읽는다. 둘 다 없거나 깨졌으면 None."""
    for p in (path, backup):
        try:
            with open(p, encoding="utf-8") as f:
                return parse(json.load(f))
        except FileNotFoundError:
            continue
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
            continue
    return None


def save(state: GameState) -> None:
    _write(SAVE_FILE, BACKUP_FILE, state.to_dict())


def load() -> GameState | None:
    return _read(SAVE_FILE, BACKUP_FILE, GameState.from_dict)


def save_records(records: Records) -> None:
    _write(RECORDS_FILE, RECORDS_BACKUP, records.to_dict())


def load_records() -> Records:
    return _read(RECORDS_FILE, RECORDS_BACKUP, Records.from_dict) or Records()


def delete() -> None:
    for path in (SAVE_FILE, BACKUP_FILE):
        path.unlink(missing_ok=True)

import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import save_manager, sprites
from game.config import LOCATIONS, REPAIR_REQUIREMENTS
from game.events import EVENTS
from game.logic import Game
from game.records import Records
from game.state import GameState


class SaveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.patches = [
            mock.patch.object(save_manager, "SAVE_DIR", self.tmp),
            mock.patch.object(save_manager, "SAVE_FILE", self.tmp / "save.json"),
            mock.patch.object(save_manager, "BACKUP_FILE", self.tmp / "save.bak.json"),
            mock.patch.object(save_manager, "RECORDS_FILE", self.tmp / "records.json"),
            mock.patch.object(save_manager, "RECORDS_BACKUP", self.tmp / "records.bak.json"),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_roundtrip(self):
        game = Game(GameState(), random.Random(1))
        game.move("crater")
        game.resolve_event(0)
        for _ in range(3):
            game.explore()
        save_manager.save(game.state)
        self.assertEqual(save_manager.load(), game.state)

    def test_pending_event_survives_restart(self):
        game = Game(GameState())
        game.move("crater")
        save_manager.save(game.state)
        self.assertEqual(save_manager.load().pending_event, "crater_glint")

    def test_corrupted_file_falls_back_to_backup(self):
        save_manager.save(GameState(day=5))
        save_manager.save(GameState(day=6))
        save_manager.SAVE_FILE.write_text("{ 깨진 파일", encoding="utf-8")
        self.assertEqual(save_manager.load().day, 5)

    def test_no_save_returns_none(self):
        self.assertIsNone(save_manager.load())
        self.assertEqual(save_manager.load_records(), Records())

    def test_records_roundtrip(self):
        records = Records(clears=2, best_days=9, achievements=["first_clear"], muted=True)
        save_manager.save_records(records)
        self.assertEqual(save_manager.load_records(), records)

    def test_v1_save_migrates(self):
        v1 = {"version": 1, "day": 4, "location": "crater", "oxygen": 50, "energy": 60,
              "inventory": {"fuel_cell": 1}, "installed": {}, "discovered": ["base", "crater"],
              "flags": {}, "log": [], "total_actions": 3, "ending": False}
        state = GameState.from_dict(v1)
        self.assertEqual((state.version, state.difficulty, state.day, state.game_over), (3, "normal", 4, False))


class LogicTest(unittest.TestCase):
    def test_full_repair_allows_launch(self):
        game = Game(GameState(inventory=dict(REPAIR_REQUIREMENTS)))
        game.repair()
        self.assertEqual(game.repair_progress(), 1)
        game.launch()
        self.assertTrue(game.state.ending)
        self.assertEqual(game.state.ending_type, "normal")

    def test_running_out_of_oxygen_returns_to_base(self):
        game = Game(GameState(location="crater", oxygen=5, inventory={"fish_can": 1}), random.Random(0))
        game.explore()
        self.assertEqual((game.state.location, game.state.day, game.state.faint_count), ("base", 2, 1))

    def test_faint_limit_per_difficulty(self):
        for diff, limit in (("easy", 5), ("normal", 3), ("hard", 2)):
            game = Game(GameState(difficulty=diff), random.Random(0))
            for i in range(limit):
                self.assertFalse(game.state.game_over, f"{diff}: {i}번 기절에서 끝나면 안 됨")
                game.state.location, game.state.oxygen = "crater", 1
                game.explore()
            self.assertTrue(game.state.game_over, diff)
            self.assertEqual(game.lives_left(), 0)

    def test_game_over_blocks_actions(self):
        game = Game(GameState(difficulty="hard", faint_count=1, location="crater", oxygen=1))
        game.explore()
        self.assertTrue(game.state.game_over)
        day = game.state.day
        game.move("base")
        game.rest()
        self.assertEqual((game.state.location, game.state.day), ("crater", day))

    def test_game_over_counted_once(self):
        records = Records()
        state = GameState(game_over=True)
        records.update_from(state)
        records.update_from(state)
        self.assertEqual((records.game_overs, records.clears), (1, 0))

    def test_difficulty_changes_oxygen_cost(self):
        easy = Game(GameState(difficulty="easy"))
        hard = Game(GameState(difficulty="hard"))
        self.assertLess(easy.move_cost("far_side"), Game(GameState()).move_cost("far_side"))
        self.assertGreater(hard.move_cost("far_side"), Game(GameState()).move_cost("far_side"))

    def test_event_blocks_actions_until_resolved(self):
        game = Game(GameState())
        game.move("crater")
        game.explore()
        self.assertEqual(game.state.energy, 100)      # 이벤트 해결 전에는 탐색 불가
        game.resolve_event(0)
        self.assertIsNone(game.state.pending_event)
        self.assertEqual(game.state.inventory.get("hull_plate"), 1)
        game.move("base")
        game.move("crater")
        self.assertIsNone(game.state.pending_event)  # 한 번 본 이벤트는 다시 안 나옴

    def test_locked_choice_needs_rescued_rabbit(self):
        game = Game(GameState(discovered=list(LOCATIONS)))
        game.state.location = "probe"
        game.move("far_side")
        self.assertEqual(game.state.pending_event, "dark_signal")
        game.resolve_event(1)                         # 달토끼를 안 구했으면 무시됨
        self.assertEqual(game.state.pending_event, "dark_signal")

    def test_rabbit_route_leads_to_rabbit_ending(self):
        game = Game(GameState(discovered=list(LOCATIONS)), random.Random(3))
        game.move("ice_cave")
        game.resolve_event(0)                         # 달토끼 구출
        game.move("base")
        game.rest()
        self.assertEqual(game.state.pending_event, "rabbit_visit")
        game.resolve_event(0)                         # 동료가 됨
        game.state.inventory.update(REPAIR_REQUIREMENTS)
        game.repair()
        game.launch()
        self.assertEqual(game.state.ending_type, "rabbit")

    def test_achievements_counted_once(self):
        records = Records()
        state = GameState(ending=True, ending_type="rabbit", difficulty="hard", day=8)
        earned = records.update_from(state)
        self.assertEqual(set(earned), {"first_clear", "speedrun", "no_faint", "hard_clear", "rabbit"})
        self.assertEqual(records.update_from(state), [])
        self.assertEqual((records.clears, records.best_days), (1, 8))


class ContentTest(unittest.TestCase):
    def test_image_assets_exist(self):
        for name in sprites.ASSET_NAMES:
            self.assertTrue((sprites.ASSETS / f"{name}.png").exists(), name)

    def test_item_effect_text(self):
        game = Game(GameState())
        self.assertEqual(game.item_effect_text("fish_can"), "체력 +40")
        self.assertEqual(game.item_effect_text("oxygen_tank"), "산소 +40")
        self.assertEqual(game.item_effect_text("rice_cake"), "체력 +70")

    def test_using_item_logs_amount(self):
        game = Game(GameState(energy=50, inventory={"fish_can": 1}))
        game.use_item("fish_can")
        self.assertEqual(game.state.energy, 90)
        self.assertIn("체력 +40 (50 → 90)", game.state.log[-1])

    def test_events_reference_known_locations(self):
        for ev in EVENTS.values():
            if "location" in ev:
                self.assertIn(ev["location"], LOCATIONS)
            for choice in ev["choices"]:
                for loc in choice.get("discover", []):
                    self.assertIn(loc, LOCATIONS)


if __name__ == "__main__":
    unittest.main()

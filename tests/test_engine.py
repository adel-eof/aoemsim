import unittest
import sys
from pathlib import Path

# Add the src folder to sys.path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.models import GameData, UnitType, Lineup
from src.mechanics import calculate_pre_battle_stats, get_counter_multiplier, resolve_healing
from src.engine import BattleEngine

class TestAOEMSimulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate JSON files relative to this test file
        cls.repo_root = Path(__file__).parent.parent
        cls.skills_path = str(cls.repo_root / "data" / "skills.json")
        cls.heroes_path = str(cls.repo_root / "data" / "heroes.json")
        
        cls.templates_path = str(cls.repo_root / "data" / "templates.json")
        cls.game_data = GameData.load_from_files(cls.skills_path, cls.heroes_path, cls.templates_path)
        cls.skills_db = cls.game_data.skills
        cls.heroes_db = cls.game_data.heroes

    def test_database_loading(self):
        self.assertIn("isolated_green_vine", self.skills_db)
        self.assertIn("cyrus_the_great", self.heroes_db)
        
        cyrus = self.heroes_db["cyrus_the_great"]
        self.assertEqual(cyrus.name, "Cyrus The Great")
        self.assertIn("commander", cyrus.skills)
        self.assertEqual(cyrus.skills["commander"].name, "Isolated Green Vine")

    def test_game_data_loading(self):
        self.assertIsInstance(self.game_data, GameData)
        self.assertGreater(len(self.game_data.skills), 0)
        self.assertGreater(len(self.game_data.heroes), 0)
        self.assertGreater(len(self.game_data.templates), 0)

    def test_get_counter_multiplier(self):
        # Archer counters Swordsman -> 1.30
        self.assertAlmostEqual(get_counter_multiplier(UnitType.ARCHER, UnitType.SWORDSMAN), 1.30)
        # Swordsman does NOT counter Cavalry -> 1.00
        self.assertAlmostEqual(get_counter_multiplier(UnitType.SWORDSMAN, UnitType.CAVALRY), 1.00)

    def test_pre_battle_stats(self):
        hero_keys = ["cyrus_the_great", "boudica", "mansa"]
        heroes = [self.heroes_db[k] for k in hero_keys]
        
        lineup = Lineup(
            heroes=heroes,
            troop_type=UnitType.PIKEMAN,
            troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0}
        )
        
        calculate_pre_battle_stats(lineup, level=50)
        # Verify that final stats are computed and non-zero
        self.assertGreater(lineup.final_stats["might"], 0.0)
        self.assertGreater(lineup.final_stats["armor"], 0.0)
        self.assertGreater(lineup.final_stats["strategy"], 0.0)

    def test_resolve_healing(self):
        lineup = Lineup(
            heroes=[None, None, None],
            troop_type=UnitType.PIKEMAN,
            troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0}
        )
        # Simulate casualties
        lineup.casualty_counters["remaining"] = 100000
        lineup.casualty_counters["lightly_wounded"] = 20000
        
        result = resolve_healing(lineup, 5000)
        self.assertEqual(result["actual_heal"], 5000)
        self.assertEqual(result["overheal"], 0)
        self.assertEqual(lineup.casualty_counters["remaining"], 105000)
        self.assertEqual(lineup.casualty_counters["lightly_wounded"], 15000)

    def test_lineup_reset(self):
        lineup = Lineup(
            heroes=[None, None, None],
            troop_type=UnitType.PIKEMAN,
            troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0}
        )
        # Modify state
        lineup.casualty_counters["remaining"] = 50000
        lineup.current_rage = 50
        
        # We need a hero to test HP reset
        cyrus = self.heroes_db["cyrus_the_great"]
        cyrus.current_hp = 10
        lineup.heroes = [cyrus, None, None]

        lineup.reset()
        
        # Verify reset
        self.assertEqual(lineup.casualty_counters["remaining"], 130000)
        self.assertEqual(lineup.current_rage, 0)
        self.assertEqual(cyrus.current_hp, 100) # Should be reset to base_hp (100)

    def test_battle_simulation(self):
        hero_keys = ["cyrus_the_great", "boudica", "mansa"]
        heroes_a = [self.heroes_db[k] for k in hero_keys]
        heroes_b = [self.heroes_db[k] for k in hero_keys]
        
        lineup_a = Lineup(
            heroes=heroes_a,
            troop_type=UnitType.PIKEMAN,
            troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0}
        )
        lineup_b = Lineup(
            heroes=heroes_b,
            troop_type=UnitType.PIKEMAN,
            troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0}
        )
        
        engine = BattleEngine(lineup_a, lineup_b, max_ticks=20)
        winner = engine.run_simulation()
        self.assertIn(winner, ["A", "B", "DRAW"])
        self.assertGreater(engine.current_tick, 0)

if __name__ == "__main__":
    unittest.main()

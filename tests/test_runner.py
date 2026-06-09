import unittest
import sys
import os
import csv
import tempfile
from pathlib import Path

# Add the src folder to sys.path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.models import load_skills_from_json, load_heroes_from_json, UnitType, Lineup
from src.runner import MonteCarloRunner

class TestMonteCarloRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate JSON files relative to this test file
        cls.repo_root = Path(__file__).parent.parent
        cls.skills_path = str(cls.repo_root / "data" / "skills.json")
        cls.heroes_path = str(cls.repo_root / "data" / "heroes.json")
        
        cls.skills_db = load_skills_from_json(cls.skills_path)
        cls.heroes_db = load_heroes_from_json(cls.heroes_path, cls.skills_db)

    def test_runner_does_not_mutate_original_lineups(self):
        hero_keys = ["cyrus_the_great", "boudica", "mansa"]
        heroes_a = [self.heroes_db[k] for k in hero_keys]
        heroes_b = [self.heroes_db[k] for k in hero_keys]
        
        initial_remaining = 130000
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
        
        # Verify initial state
        self.assertEqual(lineup_a.casualty_counters["remaining"], initial_remaining)
        self.assertEqual(lineup_b.casualty_counters["remaining"], initial_remaining)
        
        runner = MonteCarloRunner(lineup_a, lineup_b, iterations=10, enable_csv_logging=False)
        runner.run(verbose=False)
        
        # Verify state AFTER simulation (must NOT change)
        self.assertEqual(lineup_a.casualty_counters["remaining"], initial_remaining, "Original Lineup A was mutated!")
        self.assertEqual(lineup_b.casualty_counters["remaining"], initial_remaining, "Original Lineup B was mutated!")

    def test_runner_returns_correct_number_of_results(self):
        hero_keys = ["cyrus_the_great", "boudica", "mansa"]
        heroes_a = [self.heroes_db[k] for k in hero_keys]
        heroes_b = [self.heroes_db[k] for k in hero_keys]
        
        lineup_a = Lineup(heroes=heroes_a, troop_type=UnitType.PIKEMAN, troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0})
        lineup_b = Lineup(heroes=heroes_b, troop_type=UnitType.PIKEMAN, troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0})
        
        iterations = 15
        runner = MonteCarloRunner(lineup_a, lineup_b, iterations=iterations, enable_csv_logging=False)
        results = runner.run(verbose=False)
        
        self.assertEqual(len(results), iterations)

    def test_runner_result_structure(self):
        hero_keys = ["cyrus_the_great", "boudica", "mansa"]
        heroes_a = [self.heroes_db[k] for k in hero_keys]
        heroes_b = [self.heroes_db[k] for k in hero_keys]
        
        lineup_a = Lineup(heroes=heroes_a, troop_type=UnitType.PIKEMAN, troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0})
        lineup_b = Lineup(heroes=heroes_b, troop_type=UnitType.PIKEMAN, troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0})
        
        runner = MonteCarloRunner(lineup_a, lineup_b, iterations=1, enable_csv_logging=False)
        results = runner.run(verbose=False)
        
        res = results[0]
        expected_keys = ["winner", "duration_ticks", "a_remaining", "b_remaining"]
        for key in expected_keys:
            self.assertIn(key, res)

    def test_runner_writes_iteration_csv(self):
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

        with tempfile.TemporaryDirectory() as tmp_dir:
            previous_cwd = Path.cwd()
            try:
                os.chdir(tmp_dir)
                runner = MonteCarloRunner(
                    lineup_a,
                    lineup_b,
                    iterations=2,
                    enable_csv_logging=True,
                    output_dir="reports",
                )
                runner.run(verbose=False)
            finally:
                os.chdir(previous_cwd)

            csv_path = Path(tmp_dir) / "reports" / "simulation_iterations.csv"
            self.assertTrue(csv_path.exists())

            with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                rows = list(reader)

            self.assertEqual(len(rows), 2)
            for hero_name in [hero.name for hero in lineup_a.heroes if hero is not None]:
                self.assertIn(f"Damage - {hero_name}", reader.fieldnames)
            self.assertIn("Total Kills", reader.fieldnames)
            self.assertIn("Durations", reader.fieldnames)
            self.assertIn("Kill Ratio", reader.fieldnames)
            self.assertIn("Average DPS", reader.fieldnames)

if __name__ == "__main__":
    unittest.main()

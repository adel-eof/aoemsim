import copy
import csv
from pathlib import Path
from typing import TypedDict
from src.models import Lineup
from src.engine import BattleEngine

class SimulationResult(TypedDict):
    winner: str
    duration_ticks: int
    a_remaining: int
    b_remaining: int
    tracker: dict

class MonteCarloRunner:
    def __init__(
        self,
        lineup_a: Lineup,
        lineup_b: Lineup,
        iterations: int = 1000,
        enable_csv_logging: bool = True,
        output_dir: str = "reports",
    ):
        self.original_lineup_a = lineup_a
        self.original_lineup_b = lineup_b
        self.iterations = iterations
        self.enable_csv_logging = enable_csv_logging
        self.output_dir = output_dir
        self.results: list[SimulationResult] = []  # Untuk menyimpan data hasil tiap iterasi

    def run(self, verbose: bool = True) -> list[SimulationResult]:
        """Menjalankan simulasi sebanyak N kali dan mengembalikan kumpulan data mentah."""
        self.results = []
        log_interval = max(1, self.iterations // 10)
        if self.enable_csv_logging:
            self._initialize_iteration_csv()

        for i in range(self.iterations):
            # 1. Salin lineup agar bersih kembali
            la = copy.deepcopy(self.original_lineup_a)
            lb = copy.deepcopy(self.original_lineup_b)
            
            # 2. Inisialisasi engine dan jalankan
            engine = BattleEngine(la, lb)
            winner = engine.run_simulation()
            
            # 3. Catat statistik penting dari iterasi ini
            self.results.append({
                "winner": winner,
                "duration_ticks": engine.current_tick,
                "a_remaining": la.casualty_counters["remaining"],
                "b_remaining": lb.casualty_counters["remaining"],
                "tracker": engine.stats_tracker
            })
            if self.enable_csv_logging:
                self._append_iteration_csv_row(i + 1, la, lb, engine)

            if verbose and ((i + 1) % log_interval == 0 or (i + 1) == self.iterations):
                progress = ((i + 1) / self.iterations) * 100
                print(f"  Progress: {progress:.0f}% ({i + 1}/{self.iterations} iterasi selesai)...")

        return self.results

    def _initialize_iteration_csv(self) -> None:
        reports_dir = Path(self.output_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        self.iteration_csv_path = reports_dir / "simulation_iterations.csv"
        with self.iteration_csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self._csv_headers())
            writer.writeheader()

    def _csv_headers(self) -> list[str]:
        hero_names = [hero.name for hero in self.original_lineup_a.heroes if hero is not None]
        damage_columns = [f"Damage - {hero_name}" for hero_name in hero_names]
        return ["Iteration", *damage_columns, "Total Kills", "Durations", "Kill Ratio", "Average DPS"]

    def _append_iteration_csv_row(self, iteration: int, lineup_a: Lineup, lineup_b: Lineup, engine: BattleEngine) -> None:
        tracker_a = engine.stats_tracker["A"]["heroes"]
        hero_names = [hero.name for hero in self.original_lineup_a.heroes if hero is not None]

        row = {"Iteration": iteration}
        for hero_name in hero_names:
            hero_stats = tracker_a.get(hero_name, {})
            hero_total_damage = (
                hero_stats.get("normal_dmg", 0)
                + hero_stats.get("might_skill_dmg", 0)
                + hero_stats.get("strategy_skill_dmg", 0)
            )
            row[f"Damage - {hero_name}"] = hero_total_damage

        total_kills = lineup_b.casualty_counters["losses"]
        total_deaths = lineup_a.casualty_counters["losses"]
        kill_ratio = total_kills / total_deaths if total_deaths > 0 else float(total_kills)
        total_damage = sum(row[f"Damage - {hero_name}"] for hero_name in hero_names)
        average_dps = total_damage / engine.current_tick if engine.current_tick > 0 else 0.0

        row["Total Kills"] = total_kills
        row["Durations"] = engine.current_tick
        row["Kill Ratio"] = f"{kill_ratio:.4f}"
        row["Average DPS"] = f"{average_dps:.2f}"

        with self.iteration_csv_path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self._csv_headers())
            writer.writerow(row)

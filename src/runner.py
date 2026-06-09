import copy
from typing import TypedDict
from src.models import Lineup
from src.engine import BattleEngine

class SimulationResult(TypedDict):
    winner: str            # "A", "B", atau "DRAW"
    duration_ticks: int    # Detik durasi perang
    a_remaining: int       # Sisa pasukan A
    b_remaining: int       # Sisa pasukan B

class MonteCarloRunner:
    def __init__(self, lineup_a: Lineup, lineup_b: Lineup, iterations: int = 1000):
        self.original_lineup_a = lineup_a
        self.original_lineup_b = lineup_b
        self.iterations = iterations
        self.results: list[SimulationResult] = []  # Untuk menyimpan data hasil tiap iterasi

    def run(self, verbose: bool = True) -> list[SimulationResult]:
        """Menjalankan simulasi sebanyak N kali dan mengembalikan kumpulan data mentah."""
        self.results = []
        log_interval = max(1, self.iterations // 10)

        for i in range(self.iterations):
            # 1. Salin lineup agar bersih kembali
            la = copy.deepcopy(self.original_lineup_a)
            lb = copy.deepcopy(self.original_lineup_b)
            
            # 2. Inisialisasi engine dan jalankan
            engine = BattleEngine(la, lb)
            winner = engine.run_simulation()
            
            # 3. Catat statistik penting dari iterasi ini
            self.results.append({
                "winner": winner,                       # "A", "B", atau "DRAW"
                "duration_ticks": engine.current_tick,  # Detik durasi perang
                "a_remaining": la.casualty_counters["remaining"],
                "b_remaining": lb.casualty_counters["remaining"]
            })

            if verbose and ((i + 1) % log_interval == 0 or (i + 1) == self.iterations):
                progress = ((i + 1) / self.iterations) * 100
                print(f"  Progress: {progress:.0f}% ({i + 1}/{self.iterations} iterasi selesai)...")

        return self.results

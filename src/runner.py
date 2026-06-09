import copy
from src.models import Lineup
from src.engine import BattleEngine

class MonteCarloRunner:
    def __init__(self, lineup_a: Lineup, lineup_b: Lineup, iterations: int = 1000):
        self.original_lineup_a = lineup_a
        self.original_lineup_b = lineup_b
        self.iterations = iterations
        self.results = []  # Untuk menyimpan data hasil tiap iterasi

    def run(self) -> list[dict]:
        """Menjalankan simulasi sebanyak N kali dan mengembalikan kumpulan data mentah."""
        self.results = []
        for _ in range(self.iterations):
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
        return self.results

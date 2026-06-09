import time
import copy
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.models import load_skills_from_json, load_heroes_from_json, UnitType, Lineup
from src.engine import BattleEngine

def run_benchmark(num_iterations=1000):
    skills_db = load_skills_from_json("data/skills.json")
    heroes_db = load_heroes_from_json("data/heroes.json", skills_db)
    
    hero_keys = ["cyrus_the_great", "boudica", "mansa"]
    heroes_a = [heroes_db[k] for k in hero_keys]
    heroes_b = [heroes_db[k] for k in hero_keys]
    
    lineup_a_template = Lineup(
        heroes=heroes_a,
        troop_type=UnitType.PIKEMAN,
        troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0}
    )
    lineup_b_template = Lineup(
        heroes=heroes_b,
        troop_type=UnitType.PIKEMAN,
        troop_base_stats={"attack": 194.0, "defense": 146.0, "health": 146.0}
    )
    
    start_time = time.perf_counter()
    
    for _ in range(num_iterations):
        # Deep copy to ensure fresh state for each run
        la = copy.deepcopy(lineup_a_template)
        lb = copy.deepcopy(lineup_b_template)
        engine = BattleEngine(la, lb)
        engine.run_simulation()
        
    duration = time.perf_counter() - start_time
    print(f"Benchmark finished: {num_iterations} simulations in {duration:.4f} seconds.")
    print(f"Average time per simulation: {duration / num_iterations * 1000:.4f} ms")

if __name__ == "__main__":
    run_benchmark()

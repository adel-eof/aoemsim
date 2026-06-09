import argparse
from pathlib import Path
from src.engine import BattleEngine
from src.models import Lineup, UnitType, load_heroes_from_json, load_skills_from_json
from src.report import print_detailed_battle_report, print_simulation_dashboard
from src.averaged_report import print_averaged_battle_report
from src.runner import MonteCarloRunner

# Resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent
SKILLS_DB = load_skills_from_json(BASE_DIR / "data" / "skills.json")
HEROES_DB = load_heroes_from_json(BASE_DIR / "data" / "heroes.json", SKILLS_DB)
DEFAULT_TROOP_STATS = {"attack": 194.0, "defense": 146.0, "health": 146.0}


def resolve_hero_slot(hero_key: str):
    if hero_key is None:
        return None
    hero = HEROES_DB.get(hero_key)
    if hero is None:
        raise ValueError(f"Hero '{hero_key}' not found in database.")
    return hero


def build_lineup(config: dict) -> Lineup:
    hero_keys = config["heroes"]
    if len(hero_keys) != 3:
        raise ValueError("Lineup config harus berisi tepat 3 slot hero.")

    heroes = [resolve_hero_slot(hero_key) for hero_key in hero_keys]
    return Lineup(
        heroes=heroes,
        troop_type=config["troop_type"],
        troop_base_stats=config.get("troop_base_stats", DEFAULT_TROOP_STATS),
    )


def format_lineup_names(lineup: Lineup) -> str:
    return " | ".join(
        hero.name if hero is not None else "(Empty Slot)" for hero in lineup.heroes
    )


def positive_int(value: str) -> int:
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer.")
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"'{value}' must be a positive integer > 0.")
    return ivalue


def parse_args():
    parser = argparse.ArgumentParser(description="AOEM Battle Simulator CLI")
    parser.add_argument(
        "--mode",
        choices=["detailed", "monte-carlo"],
        default="detailed",
        help="Mode simulasi: pertempuran detail tunggal atau analisis Win Rate massal.",
    )
    parser.add_argument(
        "--iterations",
        type=positive_int,
        default=1000,
        help="Jumlah iterasi untuk simulasi Monte Carlo (default: 1000).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("=== AOEM SIMULATOR: THE SUSTAIN META BATTLE ===")

    # Cukup ganti isi konfigurasi ini untuk uji lineup berbeda.
    lineup_1_config = {
        "heroes": ["cyrus_the_great", "boudica", "mansa"],
        "troop_type": UnitType.PIKEMAN,
    }
    lineup_2_config = {
        "heroes": ["cyrus_the_great", "boudica", "mansa"],
        "troop_type": UnitType.PIKEMAN,
    }

    lineup_a = build_lineup(lineup_1_config)
    lineup_b = build_lineup(lineup_2_config)

    lineup_a_heroes = format_lineup_names(lineup_a)
    lineup_b_heroes = format_lineup_names(lineup_b)
    print(
        f"Simulasi Berjalan: {lineup_a_heroes} ({lineup_a.troop_type.value}) vs "
        f"{lineup_b_heroes} ({lineup_b.troop_type.value})..."
    )

    if args.mode == "monte-carlo":
        print(f"Executing Monte Carlo Simulation with {args.iterations} iterations...")
        runner = MonteCarloRunner(lineup_a, lineup_b, iterations=args.iterations)
        results = runner.run()
        print_simulation_dashboard(results, total_simulations=args.iterations)
        print_averaged_battle_report(results, lineup_a, lineup_b)
    else:
        # detailed mode
        # 3. Jalankan Pertempuran
        engine = BattleEngine(lineup_a, lineup_b)
        winner = engine.run_simulation()

        # 4. Tampilkan Laporan Detail Akhir
        print_detailed_battle_report(
            engine.stats_tracker,
            lineup_a,
            lineup_b,
            battle_duration_seconds=engine.current_tick,
        )
        print(f"KESIMPULAN: Pemenang simulasi adalah Lineup {winner}")


if __name__ == "__main__":
    main()

import argparse
from pathlib import Path
from src.engine import BattleEngine
from src.models import (
    Hero,
    Lineup,
    UnitType,
    load_heroes_from_json,
    load_skills_from_json,
    load_templates_from_json,
)
from src.report import print_detailed_battle_report, print_simulation_dashboard, print_gauntlet_report
from src.averaged_report import print_averaged_battle_report
from src.runner import MonteCarloRunner

# Resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent
SKILLS_DB = load_skills_from_json(BASE_DIR / "data" / "skills.json")
HEROES_DB = load_heroes_from_json(BASE_DIR / "data" / "heroes.json", SKILLS_DB)
TEMPLATES_DB = load_templates_from_json(BASE_DIR / "data" / "templates.json")
DEFAULT_TROOP_STATS = {"attack": 194.0, "defense": 146.0, "health": 146.0}


def resolve_hero_slot(hero_key: str):
    if hero_key is None:
        return None
    hero = HEROES_DB.get(hero_key)
    if hero is None:
        raise ValueError(f"Hero '{hero_key}' not found in database.")
    return hero


def resolve_skill(skill_key: str):
    skill = SKILLS_DB.get(skill_key)
    if skill is None:
        raise ValueError(f"Skill '{skill_key}' not found in database.")
    return skill


def build_hero_with_custom_skills(
    hero_key: str,
    custom_skills: list[str] | None = None,
    skill_overrides: dict[str, str | None] | None = None,
) -> Hero:
    base_hero = resolve_hero_slot(hero_key)
    # Clone hero instance supaya override skill tidak mengubah HEROES_DB global.
    cloned_skills = dict(base_hero.skills)

    if custom_skills is not None:
        cloned_skills = {
            slot: skill for slot, skill in cloned_skills.items() if not slot.startswith("custom_")
        }
        for index, skill_key in enumerate(custom_skills, start=1):
            cloned_skills[f"custom_{index}"] = resolve_skill(skill_key)

    if skill_overrides:
        for slot, skill_key in skill_overrides.items():
            if not slot.startswith("custom_"):
                raise ValueError(
                    "Hanya slot custom_* yang bisa dioverride. "
                    f"Slot '{slot}' tidak diperbolehkan."
                )
            if skill_key is None:
                cloned_skills.pop(slot, None)
                continue
            cloned_skills[slot] = resolve_skill(skill_key)

    return Hero(
        name=base_hero.name,
        military=base_hero.military,
        unit_types=list(base_hero.unit_types),
        base_stats=dict(base_hero.base_stats),
        growth_stats=dict(base_hero.growth_stats),
        skills=cloned_skills,
    )


def resolve_hero_config(hero_config):
    if hero_config is None:
        return None

    if isinstance(hero_config, str):
        return build_hero_with_custom_skills(hero_config)

    if isinstance(hero_config, dict):
        hero_key = hero_config.get("key")
        if not hero_key:
            raise ValueError("Hero config object harus punya field 'key'.")
        return build_hero_with_custom_skills(
            hero_key,
            custom_skills=hero_config.get("custom_skills"),
            skill_overrides=hero_config.get("skill_overrides"),
        )

    raise ValueError(
        "Format hero slot tidak valid. Gunakan string hero key, object config, atau None."
    )


def build_lineup(config: dict) -> Lineup:
    hero_keys = config["heroes"]
    if len(hero_keys) != 3:
        raise ValueError("Lineup config harus berisi tepat 3 slot hero.")

    heroes = [resolve_hero_config(hero_cfg) for hero_cfg in hero_keys]
    return Lineup(
        heroes=heroes,
        troop_type=config["troop_type"],
        troop_base_stats=config.get("troop_base_stats", DEFAULT_TROOP_STATS),
    )


def build_lineup_from_template(template_data: dict) -> Lineup:
    # Infer troop type from tags
    tags = [t.lower() for t in template_data.get("tags", [])]
    troop_type = UnitType.SWORDSMAN  # default
    if "cavalry" in tags:
        troop_type = UnitType.CAVALRY
    elif "pikeman" in tags:
        troop_type = UnitType.PIKEMAN
    elif "archer" in tags:
        troop_type = UnitType.ARCHER
    elif "swordsman" in tags:
        troop_type = UnitType.SWORDSMAN

    heroes = []
    for slot in ["commander", "sub_commander_1", "sub_commander_2"]:
        hero_cfg = template_data.get(slot)
        if hero_cfg:
            hero_key = hero_cfg.get("hero_key")
            if not hero_key:
                raise ValueError(f"Template konfigurasi hero tidak valid! 'hero_key' tidak ditemukan pada {slot}.")
                
            hero = build_hero_with_custom_skills(
                hero_key,
                custom_skills=hero_cfg.get("custom_skills"),
            )
            heroes.append(hero)
        else:
            heroes.append(None)

    return Lineup(
        heroes=heroes,
        troop_type=troop_type,
        troop_base_stats=DEFAULT_TROOP_STATS,
        template_name=template_data.get("name")
    )


def run_gauntlet_mode(lineup1: Lineup, templates_db: dict, iterations: int):
    results_summary = []
    hero_names = format_lineup_names(lineup1)

    for key, template_data in templates_db.items():
        lineup2 = build_lineup_from_template(template_data)
        # Gunakan enable_csv_logging=False agar tidak nyampah file report
        runner = MonteCarloRunner(
            lineup1, lineup2, iterations=iterations, enable_csv_logging=False
        )
        results = runner.run(verbose=False)

        wins = sum(1 for r in results if r["winner"] == "A")
        losses = sum(1 for r in results if r["winner"] == "B")
        draws = sum(1 for r in results if r["winner"] == "DRAW")

        results_summary.append({
            "template_name": template_data.get("name", key),
            "win_p": (wins / iterations) * 100,
            "lose_p": (losses / iterations) * 100,
            "draw_p": (draws / iterations) * 100
        })

    print_gauntlet_report(hero_names, iterations, results_summary)


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
    parser.add_argument(
        "--team2-template",
        type=str,
        default=None,
        help="Gunakan template lineup untuk Team 2 (misal: meta_sustain).",
    )
    parser.add_argument(
        "--run-gauntlet",
        action="store_true",
        help="Jalankan Team 1 melawan semua template yang tersedia.",
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
    lineup_a = build_lineup(lineup_1_config)

    # 1. Pilih Team 2 (Template, Gauntlet, atau Manual)
    if args.run_gauntlet:
        run_gauntlet_mode(lineup_a, TEMPLATES_DB, args.iterations)
        return

    if args.team2_template:
        if args.team2_template not in TEMPLATES_DB:
            print(
                f"Error: Template '{args.team2_template}' tidak ditemukan di data/templates.json."
            )
            return
        template_data = TEMPLATES_DB[args.team2_template]
        lineup_b = build_lineup_from_template(template_data)
    else:
        # Default/Manual config for Team 2 jika tidak ada argumen template
        lineup_2_config = {
            "heroes": [
                "cyrus_the_great",
                {
                    "key": "boudica",
                    "custom_skills": ["fearless_retribution", "golden_odyssey"],
                },
                "mansa",
            ],
            "troop_type": UnitType.PIKEMAN,
        }
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

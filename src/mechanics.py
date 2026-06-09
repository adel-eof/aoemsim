import math
from src.models import Lineup, UnitType, Military, Hero

def calculate_pre_battle_stats(lineup: Lineup, level: int = 50) -> None:
    aggregated_base = {"might": 0.0, "armor": 0.0, "strategy": 0.0, "siege": 0.0}
    for hero in lineup.heroes:
        if hero is None:
            continue
        for stat in aggregated_base.keys():
            aggregated_base[stat] += hero.get_stat_at_level(stat, level)

    military_counts = {}
    for hero in lineup.heroes:
        if hero is None:
            continue
        military_counts[hero.military] = military_counts.get(hero.military, 0) + 1

    max_same_military = max(military_counts.values()) if military_counts else 0
    if max_same_military == 3: m_multiplier = 1.30
    elif max_same_military == 2: m_multiplier = 1.20
    else: m_multiplier = 1.00

    match_count = 0
    for hero in lineup.heroes:
        if hero is None:
            continue
        if lineup.troop_type in hero.unit_types:
            match_count += 1
            
    u_multiplier = 1.00 + (0.05 * match_count)

    for stat in lineup.final_stats.keys():
        lineup.final_stats[stat] = aggregated_base[stat] * m_multiplier * u_multiplier

def get_counter_multiplier(attacker_type: UnitType, defender_type: UnitType) -> float:
    counter_map = {
        UnitType.ARCHER: UnitType.SWORDSMAN,
        UnitType.SWORDSMAN: UnitType.PIKEMAN,
        UnitType.PIKEMAN: UnitType.CAVALRY,
        UnitType.CAVALRY: UnitType.ARCHER
    }
    if counter_map.get(attacker_type) == defender_type:
        return 1.30
    return 1.00

def calculate_troops_lost(base_damage: float, counter_mult: float, crit_mult: float, troop_health: float) -> int:
    raw_loss = (base_damage * counter_mult * crit_mult) / troop_health
    return math.floor(raw_loss)

def allocate_casualty_brackets(total_lost: int) -> dict:
    lightly = math.floor(total_lost * 0.60)
    gravely = math.floor(total_lost * 0.38)
    losses = total_lost - (lightly + gravely)
    return {
        "lightly_wounded": lightly,
        "gravely_wounded": gravely,
        "losses": max(0, losses)
    }

def resolve_healing(target: Lineup, heal_amount: int) -> dict:
    actual_heal = min(heal_amount, target.casualty_counters["lightly_wounded"])
    target.casualty_counters["lightly_wounded"] -= actual_heal
    target.casualty_counters["remaining"] += actual_heal
    overheal = heal_amount - actual_heal
    return {
        "actual_heal": actual_heal,
        "overheal": overheal
    }
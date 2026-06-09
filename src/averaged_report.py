from collections import defaultdict

def print_averaged_battle_report(results: list, lineup_a, lineup_b):
    num_simulations = len(results)
    if num_simulations == 0:
        print("Tidak ada data simulasi untuk ditampilkan.")
        return

    # --- Agregasi Data dari Semua Iterasi ---
    total_skill_casts = defaultdict(lambda: defaultdict(int))
    total_skill_damage = defaultdict(lambda: defaultdict(int))
    total_hero_damage = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    total_healing = defaultdict(lambda: defaultdict(float))
    total_duration = sum(res["duration_ticks"] for res in results)
    dps_divisor = total_duration if total_duration > 0 else 1

    for res in results:
        tracker = res["tracker"]
        team_key = "A"
        # Agregasi Skill
        for s_name, s_data in tracker[team_key]["skills"].items():
            total_skill_casts[team_key][s_name] += s_data["casts"]
            total_skill_damage[team_key][s_name] += s_data["damage"]

        # Agregasi Hero
        for h_name, h_stats in tracker[team_key]["heroes"].items():
            total_hero_damage[team_key][h_name]["normal"] += h_stats["normal_dmg"]
            total_hero_damage[team_key][h_name]["might"] += h_stats["might_skill_dmg"]
            total_hero_damage[team_key][h_name]["strategy"] += h_stats["strategy_skill_dmg"]
            total_healing[team_key][h_name] += h_stats.get("healing", 0)

    # --- Tampilan Laporan ---
    print("\n" + "="*80)
    print("                AVERAGED DETAILED BATTLE REPORT")
    print(f"           (Data Agregat dari {num_simulations} Pertempuran)")
    print("="*80)

    heroes_a = " | ".join([(h.name if h is not None else "(Empty Slot)") for h in lineup_a.heroes])
    heroes_b = " | ".join([(h.name if h is not None else "(Empty Slot)") for h in lineup_b.heroes])
    print(f"[ATTACKER] Lineup A : {heroes_a} ({lineup_a.troop_type.value})")
    print(f"[DEFENDER] Lineup B : {heroes_b} ({lineup_b.troop_type.value})")
    print("-" * 80)

    print("\n[AVERAGE SKILL CASTING & DPS STATISTICS - LINEUP A]")
    team_key = "A"
    print("\n>> LINEUP A SKILLS (Rata-rata per pertempuran):")
    if not total_skill_casts[team_key]:
        print("   (Tidak ada skill yang terpicu)")
    for s_name in sorted(total_skill_casts[team_key].keys()):
        avg_casts = total_skill_casts[team_key][s_name] / num_simulations
        avg_dps = total_skill_damage[team_key][s_name] / dps_divisor
        print(f"   - {s_name:<25} : Keluar {avg_casts:>5.2f} kali | Avg DPS: {avg_dps:,.2f}")

    print("\n" + "-" * 80)
    print("[AVERAGE HERO DPS BREAKDOWN - LINEUP A]")
    print(f"{'HERO NAME':<20} | {'NORMAL':<9} | {'MIGHT':<9} | {'STRATEGY':<9} | {'HEAL':<9} | {'AVG DPS':<10}")
    print("-" * 96)

    # Menggunakan nama hero dari lineup asli untuk menjaga urutan
    hero_names = [h.name for h in lineup_a.heroes if h is not None]
    for h_name in hero_names:
        avg_norm_dps = total_hero_damage[team_key][h_name]["normal"] / dps_divisor
        avg_might_dps = total_hero_damage[team_key][h_name]["might"] / dps_divisor
        avg_strat_dps = total_hero_damage[team_key][h_name]["strategy"] / dps_divisor
        avg_heal = total_healing[team_key][h_name] / num_simulations
        avg_total_dps = avg_norm_dps + avg_might_dps + avg_strat_dps

        if avg_total_dps > 0 or avg_heal > 0:
            print(f"[A] {h_name:<16} | {avg_norm_dps:<9,.2f} | {avg_might_dps:<9,.2f} | {avg_strat_dps:<9,.2f} | {avg_heal:<9,.0f} | {avg_total_dps:<10,.2f}")
    print("="*80 + "\n")

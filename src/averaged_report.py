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

    for res in results:
        tracker = res["tracker"]
        for team_key in ["A", "B"]:
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

    print("\n[AVERAGE SKILL CASTING & DAMAGE STATISTICS]")
    for team_key, team_name in [("A", "LINEUP A"), ("B", "LINEUP B")]:
        print(f"\n>> {team_name} SKILLS (Rata-rata per pertempuran):")
        if not total_skill_casts[team_key]:
            print("   (Tidak ada skill yang terpicu)")
            continue
        for s_name in sorted(total_skill_casts[team_key].keys()):
            avg_casts = total_skill_casts[team_key][s_name] / num_simulations
            avg_dmg = total_skill_damage[team_key][s_name] / num_simulations
            print(f"   - {s_name:<25} : Keluar {avg_casts:>5.2f} kali | Rata-rata Dmg: {avg_dmg:,.0f}")

    print("\n" + "-" * 80)
    print("[AVERAGE HERO DAMAGE BREAKDOWN]")
    print(f"{'HERO NAME':<20} | {'NORMAL':<9} | {'MIGHT':<9} | {'STRATEGY':<9} | {'HEAL':<9} | {'TOTAL DMG':<10}")
    print("-" * 96)

    for team_key in ["A", "B"]:
        # Menggunakan nama hero dari lineup asli untuk menjaga urutan
        hero_names = [h.name for h in (lineup_a.heroes if team_key == "A" else lineup_b.heroes) if h is not None]
        for h_name in hero_names:
            avg_norm = total_hero_damage[team_key][h_name]["normal"] / num_simulations
            avg_might = total_hero_damage[team_key][h_name]["might"] / num_simulations
            avg_strat = total_hero_damage[team_key][h_name]["strategy"] / num_simulations
            avg_heal = total_healing[team_key][h_name] / num_simulations
            avg_total = avg_norm + avg_might + avg_strat
            
            if avg_total > 0 or avg_heal > 0:
                print(f"[{team_key}] {h_name:<16} | {avg_norm:<9,.0f} | {avg_might:<9,.0f} | {avg_strat:<9,.0f} | {avg_heal:<9,.0f} | {avg_total:<10,.0f}")
    print("="*80 + "\n")

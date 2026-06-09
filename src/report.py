def print_simulation_dashboard(results: list, total_simulations: int):
    wins_a = sum(1 for r in results if r["winner"] == "A")
    wins_b = sum(1 for r in results if r["winner"] == "B")
    draws = sum(1 for r in results if r["winner"] == "DRAW")
    win_rate_a = (wins_a / total_simulations) * 100
    avg_rem_a = sum(r["a_remaining"] for r in results if r["winner"] == "A") / (wins_a or 1)
    avg_rem_b = sum(r["b_remaining"] for r in results if r["winner"] == "B") / (wins_b or 1)
    
    durations = [r["duration_ticks"] for r in results]
    avg_duration = sum(durations) / (len(durations) or 1)
    max_duration = max(durations) if durations else 0
    min_duration = min(durations) if durations else 0

    print("\n" + "="*70)
    print("                 ADVANCED BATTLE SIMULATION REPORT")
    print("="*70)
    print("[GENERAL RESULT]")
    print(f"Total Iterasi : {total_simulations} Pertempuran")
    print(f"Win Rate A    : {win_rate_a:.2f}% ({wins_a} Menang | {wins_b} Kalah | {draws} Seri)")
    print("-" * 70)
    print("[TROOP SURVIVABILITY METRICS]")
    print(f"Lineup A (Jika Menang) rata-rata menyisakan : {avg_rem_a:,.0f} Pasukan")
    print(f"Lineup B (Jika Menang) rata-rata menyisakan : {avg_rem_b:,.0f} Pasukan")
    print("-" * 70)
    print("[BATTLE DURATION METRICS]")
    print(f"Rata-rata Durasi : {avg_duration:.1f} detik (Min: {min_duration}s | Max: {max_duration}s)")
    print("="*70 + "\n")

def print_detailed_battle_report(tracker: dict, lineup_a, lineup_b, battle_duration_seconds: int = 0):
    print("\n" + "="*80)
    print("                      DETAILED BATTLE REPORT")
    print("="*80)
    
    heroes_a = " | ".join([(h.name if h is not None else "(Empty Slot)") for h in lineup_a.heroes])
    heroes_b = " | ".join([(h.name if h is not None else "(Empty Slot)") for h in lineup_b.heroes])
    print(f"[ATTACKER] Lineup A : {heroes_a} ({lineup_a.troop_type.value})")
    print(f"[DEFENDER] Lineup B : {heroes_b} ({lineup_b.troop_type.value})")
    print(f"[BATTLE DURATION]    : {battle_duration_seconds} detik")
    print("-" * 80)
    
    print(f"{'TROOP METRICS':<25} | {'LINEUP A':<23} | {'LINEUP B':<23}")
    print("-" * 80)
    print(f"{'Initial Troops':<25} | {130000:<23,d} | {130000:<23,d}")
    print(f"{'Lightly Wounded':<25} | {lineup_a.casualty_counters['lightly_wounded']:<23,d} | {lineup_b.casualty_counters['lightly_wounded']:<23,d}")
    print(f"{'Gravely Wounded':<25} | {lineup_a.casualty_counters['gravely_wounded']:<23,d} | {lineup_b.casualty_counters['gravely_wounded']:<23,d}")
    print(f"{'Losses (Dead)':<25} | {lineup_a.casualty_counters['losses']:<23,d} | {lineup_b.casualty_counters['losses']:<23,d}")
    print(f"{'Remaining Troops':<25} | {lineup_a.casualty_counters['remaining']:<23,d} | {lineup_b.casualty_counters['remaining']:<23,d}")
    print("-" * 80)
    
    print("\n[SKILL CASTING & DAMAGE STATISTICS]")
    for team_key, team_name in [("A", "LINEUP A"), ("B", "LINEUP B")]:
        print(f"\n>> {team_name} SKILLS:")
        skills = tracker[team_key]["skills"]
        if not skills:
            print("   (Tidak ada skill yang terpicu)")
        for s_name, s_data in skills.items():
            print(f"   - {s_name:<25} : Keluar {s_data['casts']:>2} kali | Total Dmg: {s_data['damage']:,d}")
            
    print("\n" + "-" * 80)
    print("[HERO DAMAGE BREAKDOWN]")
    print(f"{'HERO NAME':<20} | {'NORMAL':<9} | {'MIGHT':<9} | {'STRATEGY':<9} | {'HEAL':<9} | {'TOTAL DMG':<10}")
    print("-" * 96)
    
    for team_key in ["A", "B"]:
        for h_name, h_stats in tracker[team_key]["heroes"].items():
            norm_dmg = h_stats["normal_dmg"]
            might_dmg = h_stats["might_skill_dmg"]
            strat_dmg = h_stats["strategy_skill_dmg"]
            heal_done = h_stats.get("healing", 0)
            total_dmg = norm_dmg + might_dmg + strat_dmg
            if total_dmg > 0 or heal_done > 0:
                print(f"[{team_key}] {h_name:<16} | {norm_dmg:<9,d} | {might_dmg:<9,d} | {strat_dmg:<9,d} | {heal_done:<9,d} | {total_dmg:<10,d}")
    print("="*80 + "\n")
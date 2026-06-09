import random
import math
from src.models import Lineup, SkillType, Skill
from src.mechanics import (
    calculate_pre_battle_stats,
    get_counter_multiplier, 
    calculate_troops_lost, 
    allocate_casualty_brackets, 
    resolve_healing
)

class BattleEngine:
    def __init__(self, lineup_a: Lineup, lineup_b: Lineup, max_ticks: int = 300):
        self.lineup_a = lineup_a
        self.lineup_b = lineup_b
        self.max_ticks = max_ticks
        self.current_tick = 0

        # Hitung stat akhir lineup dari data hero sebelum simulasi berjalan.
        calculate_pre_battle_stats(self.lineup_a)
        calculate_pre_battle_stats(self.lineup_b)

        # Terapkan efek start-of-battle (mis. initial rage dari commander skill).
        self._apply_battle_start_effects(self.lineup_a)
        self._apply_battle_start_effects(self.lineup_b)
        
        self.stats_tracker = {
            "A": {"heroes": {}, "skills": {}},
            "B": {"heroes": {}, "skills": {}}
        }
        self.skill_cooldowns = {
            "A": {},
            "B": {}
        }
        
        for team_key, lineup in [("A", lineup_a), ("B", lineup_b)]:
            for idx, hero in enumerate(lineup.heroes, start=1):
                hero_key = hero.name if hero is not None else f"Unit Slot {idx}"
                self.stats_tracker[team_key]["heroes"][hero_key] = {
                    "normal_dmg": 0, "might_skill_dmg": 0, "strategy_skill_dmg": 0, "healing": 0
                }

    def _apply_battle_start_effects(self, lineup: Lineup):
        if not lineup.heroes:
            return
        if lineup.heroes[0] is None:
            return
        commander = lineup.heroes[0].skills.get("commander")
        if not commander:
            return

        for effect in commander.effects:
            if effect.get("type") != "RAGE":
                continue
            if effect.get("timing") != "BATTLE_START":
                continue
            if effect.get("target", "SELF") != "SELF":
                continue

            lineup.current_rage += int(effect.get("value", 0))

    def _safe_stat(self, lineup: Lineup, stat_name: str, fallback: float = 300.0) -> float:
        value = lineup.final_stats.get(stat_name, 0.0)
        return value if value > 0 else fallback

    def _damage_scaler(self, lineup: Lineup, dmg_type: str) -> float:
        if dmg_type == "MIGHT":
            return self._safe_stat(lineup, "might") / 300.0
        if dmg_type == "STRATEGY":
            return self._safe_stat(lineup, "strategy") / 300.0
        return (self._safe_stat(lineup, "might") + self._safe_stat(lineup, "strategy")) / 600.0

    def _healing_scaler(self, lineup: Lineup) -> float:
        return self._safe_stat(lineup, "strategy") / 300.0

    def _mitigation_multiplier(self, target: Lineup, dmg_type: str) -> float:
        # Tuning v3: mitigation diringankan lagi agar pertahanan tidak terlalu dominan,
        # sambil tetap mempertahankan perbedaan MIGHT vs STRATEGY.
        troop_defense_weight = 1.30
        mitigation_scale = 0.27

        armor = self._safe_stat(target, "armor")
        strategy = self._safe_stat(target, "strategy")
        troop_defense = target.troop_stats.get("defense", 146.0)

        if dmg_type == "STRATEGY":
            defense_pool = (strategy * 0.70) + (armor * 0.15) + (troop_defense * troop_defense_weight)
        elif dmg_type == "MIGHT":
            defense_pool = (armor * 0.70) + (strategy * 0.15) + (troop_defense * troop_defense_weight)
        else:
            defense_pool = (armor * 0.55) + (strategy * 0.25) + (troop_defense * troop_defense_weight)

        mitigation = 300.0 / (300.0 + (defense_pool * mitigation_scale))
        return max(0.25, min(1.0, mitigation))

    def _get_modifier_total(self, lineup: Lineup, attribute: str) -> float:
        return sum(mod["value"] for mod in lineup.active_modifiers if mod["attribute"] == attribute)

    def _get_damage_boost(self, lineup: Lineup, dmg_type: str) -> float:
        base_boost = self._get_modifier_total(lineup, "DAMAGE_BOOST")
        if dmg_type == "MIGHT":
            return base_boost + self._get_modifier_total(lineup, "MIGHT_DAMAGE_BOOST")
        if dmg_type == "STRATEGY":
            return base_boost + self._get_modifier_total(lineup, "STRATEGY_DAMAGE_BOOST")
        return base_boost

    def _is_status_active(self, lineup: Lineup, status: str) -> bool:
        return any(s["status"] == status and s["expires_at"] > self.current_tick for s in lineup.active_statuses)

    def _is_status_immune(self, lineup: Lineup, status: str) -> bool:
        return lineup.status_immunities.get(status, 0) > self.current_tick

    def _refresh_or_add_status(self, lineup: Lineup, status: str, duration: int):
        expires_at = self.current_tick + max(0, duration)
        for current in lineup.active_statuses:
            if current["status"] == status:
                current["expires_at"] = max(current["expires_at"], expires_at)
                return
        lineup.active_statuses.append({"status": status, "expires_at": expires_at})

    def _remove_status(self, lineup: Lineup, status: str):
        lineup.active_statuses = [s for s in lineup.active_statuses if s["status"] != status]

    def _apply_crowd_control(self, target: Lineup, status: str, chance: float, duration: int):
        if random.random() > chance:
            return
        if self._is_status_immune(target, status):
            return
        self._refresh_or_add_status(target, status, duration)

    def _update_statuses(self, lineup: Lineup):
        persisted = []
        for status_entry in lineup.active_statuses:
            if status_entry["expires_at"] > self.current_tick:
                persisted.append(status_entry)
                continue
            ended_status = status_entry["status"]
            if ended_status in {"SILENCE", "DISARM", "INCAPACITATION"}:
                lineup.status_immunities[ended_status] = self.current_tick + 3
        lineup.active_statuses = persisted

    def _tick_dot_effects(self, victim: Lineup, enemy: Lineup):
        persisted_dots = []
        for dot in victim.active_dots:
            if dot["expires_at"] <= self.current_tick:
                continue

            dot_rate = dot.get("rate", 0.0)
            dot_damage_type = dot.get("damage_type", "STRATEGY")
            source_scaler = self._damage_scaler(enemy, dot_damage_type)
            base_dot_dmg = enemy.casualty_counters["remaining"] * 15.0 * dot_rate * source_scaler
            loss = self.apply_damage(victim, base_dot_dmg, 1.0, dot_damage_type)

            if dot.get("source_team") and dot.get("source_hero"):
                self.record_damage(
                    dot["source_team"],
                    dot["source_hero"],
                    loss,
                    dot_damage_type,
                    dot.get("source_skill")
                )

            persisted_dots.append(dot)
        victim.active_dots = persisted_dots

    def _queue_charge_skill(self, caster: Lineup, hero_index: int, hero_name: str, skill: Skill, charge_duration: int):
        if charge_duration <= 0:
            return False

        for pending in caster.pending_charges:
            if pending["hero_index"] == hero_index and pending["skill_name"] == skill.name:
                return True

        caster.pending_charges.append({
            "hero_index": hero_index,
            "hero_name": hero_name,
            "skill": skill,
            "skill_name": skill.name,
            "execute_at": self.current_tick + charge_duration
        })
        self._refresh_or_add_status(caster, "CHARGING", charge_duration)
        return True

    def _resolve_pending_charges(self, caster: Lineup, target: Lineup, team_key: str):
        if not caster.pending_charges:
            return

        still_pending = []
        for pending in caster.pending_charges:
            if pending["execute_at"] > self.current_tick:
                still_pending.append(pending)
                continue

            if self._is_status_active(caster, "SILENCE") or self._is_status_active(caster, "INCAPACITATION"):
                continue

            self.execute_dsl_effects(
                pending["skill"],
                caster,
                target,
                team_key,
                pending["hero_name"],
                hero_index=pending["hero_index"]
            )

        caster.pending_charges = still_pending
        if not caster.pending_charges:
            self._remove_status(caster, "CHARGING")

    def _run_turn_based_skills(self, hero, caster: Lineup, target: Lineup, team_key: str, hero_index: int):
        turn_based_skills = [s for s in hero.skills.values() if s and s.type == SkillType.TURN_BASED]
        for skill in turn_based_skills:
            # Turn-based skills with explicit triggers are handled by their event hooks.
            if any(effect.get("trigger") for effect in skill.effects):
                continue
            if random.random() <= skill.activation_chance:
                self.execute_dsl_effects(skill, caster, target, team_key, hero.name, hero_index=hero_index)

    def _get_trigger_interval(self, skill: Skill, trigger_name: str) -> int:
        interval_values = [
            int(effect.get("interval", 0))
            for effect in skill.effects
            if effect.get("trigger") == trigger_name and effect.get("interval") is not None
        ]
        return max(interval_values) if interval_values else 0

    def _run_periodic_trigger_skills(self, caster: Lineup, target: Lineup, team_key: str):
        for hero_index, hero in enumerate(caster.heroes):
            if hero is None:
                continue

            periodic_skills = [
                s for s in hero.skills.values()
                if s and s.type in {SkillType.PASSIVE, SkillType.TURN_BASED}
                and any(effect.get("trigger") == "PERIODIC" for effect in s.effects)
            ]

            for skill in periodic_skills:
                if self._is_skill_on_cooldown(team_key, hero.name, skill.name):
                    continue

                # PERIODIC trigger follows guaranteed interval activation behavior.
                self.execute_dsl_effects(skill, caster, target, team_key, hero.name, hero_index=hero_index)

                interval = self._get_trigger_interval(skill, "PERIODIC")
                cooldown = interval if interval > 0 else self._get_skill_cooldown(skill, "PERIODIC")
                self._set_skill_cooldown(team_key, hero.name, skill.name, cooldown)

    def _get_skill_cooldown(self, skill: Skill, trigger_name: str) -> int:
        cooldown_values = [
            int(effect.get("cooldown", 0))
            for effect in skill.effects
            if effect.get("trigger") == trigger_name and effect.get("cooldown") is not None
        ]
        return max(cooldown_values) if cooldown_values else 0

    def _is_skill_on_cooldown(self, team_key: str, hero_name: str, skill_name: str) -> bool:
        key = f"{hero_name}::{skill_name}"
        return self.skill_cooldowns[team_key].get(key, 0) > self.current_tick

    def _set_skill_cooldown(self, team_key: str, hero_name: str, skill_name: str, cooldown: int):
        if cooldown <= 0:
            return
        key = f"{hero_name}::{skill_name}"
        self.skill_cooldowns[team_key][key] = self.current_tick + cooldown

    def _get_normal_attack_count(self, attacker: Lineup) -> int:
        from_status = self._is_status_active(attacker, "DOUBLE_ATTACK")
        from_modifier = self._get_modifier_total(attacker, "DOUBLE_ATTACK") > 0
        return 2 if (from_status or from_modifier) else 1

    def _roll_critical_multiplier(self, attacker: Lineup) -> float:
        crit_chance = max(0.0, min(0.75, self._get_modifier_total(attacker, "CRIT_CHANCE")))
        if crit_chance <= 0.0:
            return 1.0
        if random.random() <= crit_chance:
            attacker.combat_trackers["critical_hits"] += 1
            return 1.5
        return 1.0

    def _resolve_buff_target(self, effect_target: str, caster: Lineup, target: Lineup) -> Lineup:
        if effect_target in {"SELF", "ALLY", "ALL_ALLIES", "NEXT_HERO", "FRIENDLY"}:
            return caster
        return target

    def record_skill_cast(self, team_key: str, skill_name: str):
        if skill_name not in self.stats_tracker[team_key]["skills"]:
            self.stats_tracker[team_key]["skills"][skill_name] = {"casts": 0, "damage": 0, "healing": 0}
        self.stats_tracker[team_key]["skills"][skill_name]["casts"] += 1

    def record_damage(self, team_key: str, hero_name: str, dmg_amount: int, dmg_type: str, skill_name: str = None):
        target = self.stats_tracker[team_key]["heroes"].get(hero_name)
        if target:
            if dmg_type == "NORMAL": target["normal_dmg"] += dmg_amount
            elif dmg_type == "MIGHT": target["might_skill_dmg"] += dmg_amount
            elif dmg_type == "STRATEGY": target["strategy_skill_dmg"] += dmg_amount

        if skill_name:
            if skill_name not in self.stats_tracker[team_key]["skills"]:
                self.stats_tracker[team_key]["skills"][skill_name] = {"casts": 0, "damage": 0, "healing": 0}
            self.stats_tracker[team_key]["skills"][skill_name]["damage"] += dmg_amount

    def record_healing(self, team_key: str, hero_name: str, heal_amount: int, skill_name: str = None):
        target = self.stats_tracker[team_key]["heroes"].get(hero_name)
        if target:
            target["healing"] += heal_amount

        if skill_name:
            if skill_name not in self.stats_tracker[team_key]["skills"]:
                self.stats_tracker[team_key]["skills"][skill_name] = {"casts": 0, "damage": 0, "healing": 0}
            self.stats_tracker[team_key]["skills"][skill_name]["healing"] += heal_amount

    def run_simulation(self) -> str:
        while self.current_tick < self.max_ticks and self.lineup_a.is_alive() and self.lineup_b.is_alive():
            self.current_tick += 1

            # Periodic effects are evaluated once per simulation tick.
            self._tick_dot_effects(self.lineup_a, self.lineup_b)
            self._tick_dot_effects(self.lineup_b, self.lineup_a)
            self._run_periodic_trigger_skills(self.lineup_a, self.lineup_b, "A")
            self._run_periodic_trigger_skills(self.lineup_b, self.lineup_a, "B")
            self._resolve_pending_charges(self.lineup_a, self.lineup_b, "A")
            self._resolve_pending_charges(self.lineup_b, self.lineup_a, "B")

            self.process_turn(self.lineup_a, self.lineup_b, "A", "B")
            if not self.lineup_b.is_alive(): break
            self.process_turn(self.lineup_b, self.lineup_a, "B", "A")

        if self.lineup_a.is_alive() and not self.lineup_b.is_alive(): return "A"
        if self.lineup_b.is_alive() and not self.lineup_a.is_alive(): return "B"
        return "DRAW"

    def apply_damage(self, target: Lineup, base_damage: float, counter_mult: float, dmg_type: str = "NORMAL", crit_mult: float = 1.0) -> int:
        if not target.is_alive(): return 0
        
        dmg_reduction = sum(mod["value"] for mod in target.active_modifiers if mod["attribute"] == "DAMAGE_REDUCTION")
        dmg_reduction = min(dmg_reduction, 0.80) 
        mitigation_mult = self._mitigation_multiplier(target, dmg_type)
        final_damage = base_damage * (1.0 - dmg_reduction) * mitigation_mult
        
        troop_health = target.troop_stats.get("health", 146.0)
        loss = calculate_troops_lost(final_damage, counter_mult, crit_mult, troop_health)
        loss = min(loss, target.casualty_counters["remaining"])
        
        if loss > 0:
            target.casualty_counters["remaining"] -= loss
            brackets = allocate_casualty_brackets(loss)
            target.casualty_counters["lightly_wounded"] += brackets["lightly_wounded"]
            target.casualty_counters["gravely_wounded"] += brackets["gravely_wounded"]
            target.casualty_counters["losses"] += brackets["losses"]
        return loss

    def update_modifiers(self, lineup: Lineup):
        lineup.active_modifiers = [
            mod for mod in lineup.active_modifiers 
            if mod["expires_at"] > self.current_tick
        ]
        self._update_statuses(lineup)

    def execute_dsl_effects(self, skill: Skill, caster: Lineup, target: Lineup, team_key: str, hero_name: str, hero_index: int = -1):
        self.record_skill_cast(team_key, skill.name)
        for effect in skill.effects:
            if effect["type"] == "DAMAGE":
                rate = effect.get("rate", 1.0)
                dmg_type = effect.get("damage_type", "MIGHT")
                damage_boost = self._get_damage_boost(caster, dmg_type)
                stat_scaler = self._damage_scaler(caster, dmg_type)
                burst_base = caster.casualty_counters["remaining"] * 15.0 * rate * (1.0 + damage_boost) * stat_scaler
                loss = self.apply_damage(target, burst_base, 1.0, dmg_type)
                self.record_damage(team_key, hero_name, loss, dmg_type, skill.name)
            elif effect["type"] == "HEAL":
                rate = effect.get("rate", 1.0)
                heal_amount = math.floor(caster.casualty_counters["remaining"] * 0.15 * rate * self._healing_scaler(caster))
                healing_result = resolve_healing(caster, heal_amount)
                self.record_healing(team_key, hero_name, healing_result["actual_heal"], skill.name)
            elif effect["type"] == "BUFF":
                buff_target = self._resolve_buff_target(effect.get("target", "SELF"), caster, target)
                expires_at = self.current_tick + effect.get("duration", 0)

                max_stacks = effect.get("max_stacks")
                if max_stacks is not None:
                    same_stacks = [
                        mod for mod in buff_target.active_modifiers
                        if mod.get("attribute") == effect["attribute"] and mod.get("source_skill") == skill.name
                    ]
                    if len(same_stacks) >= int(max_stacks):
                        oldest = min(same_stacks, key=lambda m: m.get("expires_at", 0))
                        oldest["expires_at"] = max(oldest.get("expires_at", 0), expires_at)
                        continue

                buff_target.active_modifiers.append({
                    "attribute": effect["attribute"],
                    "value": effect["value"],
                    "expires_at": expires_at,
                    "source_skill": skill.name
                })
            elif effect["type"] == "CHARGE":
                self._queue_charge_skill(caster, hero_index, hero_name, skill, int(effect.get("duration", 0)))
            elif effect["type"] == "DOT":
                duration = effect.get("duration", 0)
                target.active_dots.append({
                    "dot_type": effect.get("dot_type", "GENERIC"),
                    "damage_type": "STRATEGY" if effect.get("dot_type") == "BURN" else effect.get("damage_type", "MIGHT"),
                    "rate": effect.get("rate", 0.0),
                    "expires_at": self.current_tick + duration,
                    "source_team": team_key,
                    "source_hero": hero_name,
                    "source_skill": skill.name
                })
            elif effect["type"] == "CROWD_CONTROL":
                self._apply_crowd_control(
                    target,
                    effect.get("status", "SILENCE"),
                    effect.get("chance", 1.0),
                    effect.get("duration", 0)
                )

    def trigger_on_hit_passive_skills(self, attacker: Lineup, defender: Lineup, att_team: str, def_team: str):
        """Mengevaluasi skill pasif defender yang terpicu saat menerima pukulan Normal Attack"""
        
        # Tambahkan tracker hit normal attack received pada defender
        defender.combat_trackers["normal_attacks_received"] += 1
        
        for hero in defender.heroes:
            if hero is None:
                continue
            # Pemicu tipe 1: Akumulasi setelah terkena 12 kali pukulan normal
            if defender.combat_trackers["normal_attacks_received"] % 12 == 0:
                # Ambil skill pasif penumpuk hit seperti Devout Radiance dan Golden Odyssey
                hit_skills = [s for s in hero.skills.values() if s and s.name in ["Devout Radiance", "Golden Odyssey"]]
                for skill in hit_skills:
                    self.execute_dsl_effects(skill, defender, attacker, def_team, hero.name)
            
            # Trigger umum untuk skill PASSIVE/TURN_BASED berbasis event ON_HIT_BY_NORMAL_ATTACK.
            reactive_skills = [
                s for s in hero.skills.values()
                if s and s.type in {SkillType.PASSIVE, SkillType.TURN_BASED}
                and any(effect.get("trigger") == "ON_HIT_BY_NORMAL_ATTACK" for effect in s.effects)
            ]
            for skill in reactive_skills:
                if self._is_skill_on_cooldown(def_team, hero.name, skill.name):
                    continue
                if random.random() <= skill.activation_chance:
                    self.execute_dsl_effects(skill, defender, attacker, def_team, hero.name)
                    self._set_skill_cooldown(
                        def_team,
                        hero.name,
                        skill.name,
                        self._get_skill_cooldown(skill, "ON_HIT_BY_NORMAL_ATTACK")
                    )

    def process_turn(self, attacker: Lineup, defender: Lineup, att_team: str, def_team: str):
        self.update_modifiers(attacker)
        self.update_modifiers(defender)
        
        for index in range(3):
            hero = attacker.heroes[index] if index < len(attacker.heroes) else None
            # Status gate: incapacitated lineups cannot perform damaging actions this turn.
            if self._is_status_active(attacker, "INCAPACITATION"):
                continue

            # 1. Commander Skill Phase
            if hero is not None and index == 0:
                cmd = hero.skills.get("commander")

                if cmd and not self._is_status_active(attacker, "SILENCE") and attacker.current_rage >= cmd.rage_cost:
                    self.execute_dsl_effects(cmd, attacker, defender, att_team, hero.name, hero_index=index)
                    attacker.current_rage -= cmd.rage_cost

            # 1b. Turn-Based Skill Phase
            if hero is not None:
                self._run_turn_based_skills(hero, attacker, defender, att_team, index)
            
            # 2. Active Skills Phase
            if hero is not None and not self._is_status_active(attacker, "SILENCE"):
                for skill in [s for s in hero.skills.values() if s and s.type == SkillType.ACTIVE]:
                    if random.random() <= skill.activation_chance:
                        self.execute_dsl_effects(skill, attacker, defender, att_team, hero.name, hero_index=index)

            # 3. Normal Attack Phase
            if hero is None or not self._is_status_active(attacker, "DISARM"):
                normal_attack_count = self._get_normal_attack_count(attacker)
                for _ in range(normal_attack_count):
                    damage_boost = self._get_damage_boost(attacker, "MIGHT")
                    base_normal_dmg = (attacker.casualty_counters["remaining"] * 2.5) * (1.0 + damage_boost) * self._damage_scaler(attacker, "MIGHT")
                    mult = get_counter_multiplier(attacker.troop_type, defender.troop_type)
                    crit_mult = self._roll_critical_multiplier(attacker)

                    loss = self.apply_damage(defender, base_normal_dmg, mult, "NORMAL", crit_mult)
                    source_name = hero.name if hero is not None else f"Unit Slot {index + 1}"
                    self.record_damage(att_team, source_name, loss, "NORMAL")
                    attacker.current_rage += 10

                    # Counter-passive trigger for each landed normal attack instance.
                    self.trigger_on_hit_passive_skills(attacker, defender, att_team, def_team)

                    # 4. Secondary Strikes Phase
                    if hero is not None:
                        for skill in [s for s in hero.skills.values() if s and s.type == SkillType.SECONDARY_STRIKE]:
                            if random.random() <= skill.activation_chance:
                                self.execute_dsl_effects(skill, attacker, defender, att_team, hero.name, hero_index=index)
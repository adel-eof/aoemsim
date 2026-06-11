import json
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

class Military(Enum):
    WARRIOR = "Warrior"
    MARSHAL = "Marshal"
    TACTICIAN = "Tactician"

class UnitType(Enum):
    SWORDSMAN = "Swordsman"
    PIKEMAN = "Pikeman"
    CAVALRY = "Cavalry"
    ARCHER = "Archer"

class SkillType(Enum):
    ACTIVE = "Active"
    TURN_BASED = "Turn-Based"
    SECONDARY_STRIKE = "Secondary Strike"
    PASSIVE = "Passive"
    COMMANDER = "Commander"

class Skill:
    def __init__(self, name: str, skill_type: SkillType, activation_chance: float, rage_cost: int = 0, effects: List[Dict[str, Any]] = None):
        self.name = name
        self.type = skill_type
        self.activation_chance = activation_chance
        self.rage_cost = rage_cost
        self.effects = effects if effects else []

class Hero:
    def __init__(self, name: str, military: Military, unit_types: List[UnitType], base_stats: Dict[str, float], growth_stats: Dict[str, float], skills: Dict[str, Skill]):
        self.name = name
        self.military = military
        self.unit_types = unit_types
        self.base_stats = base_stats
        self.growth_stats = growth_stats
        self.skills = skills
        self.base_hp = 100
        self.current_hp = 100

    def get_stat_at_level(self, stat_name: str, level: int = 50) -> float:
        base = self.base_stats.get(stat_name, 0.0)
        growth = self.growth_stats.get(stat_name, 0.0)
        return base + (growth * (level - 1))

class Lineup:
    def __init__(self, heroes: List[Optional[Hero]], troop_type: UnitType, troop_base_stats: Dict[str, float], template_name: str = None):
        if len(heroes) != 3:
            raise ValueError("Satu lineup harus berisi tepat 3 hero!")
        self.heroes = heroes  
        self.troop_type = troop_type
        self.troop_stats = troop_base_stats
        self.template_name = template_name
        self.final_stats = {"might": 0.0, "armor": 0.0, "strategy": 0.0, "siege": 0.0}
        self.current_rage = 0
        self.casualty_counters = {
            "remaining": 130000,
            "lightly_wounded": 0,
            "gravely_wounded": 0,
            "losses": 0
        }
        self.combat_trackers = {
            "normal_attacks_received": 0,
            "counterattack_count": 0,
            "critical_hits": 0
        }
        self.active_modifiers = []
        self.active_dots = []
        self.active_statuses = []
        self.status_immunities = {}
        self.pending_charges = []

    def is_alive(self) -> bool:
        return self.casualty_counters["remaining"] > 0

    def reset(self) -> None:
        """Reset the lineup state for a new simulation iteration."""
        for hero in self.heroes:
            if hero is not None:
                hero.current_hp = hero.base_hp
        
        self.current_rage = 0
        self.casualty_counters = {
            "remaining": 130000,
            "lightly_wounded": 0,
            "gravely_wounded": 0,
            "losses": 0
        }
        self.combat_trackers = {
            "normal_attacks_received": 0,
            "counterattack_count": 0,
            "critical_hits": 0
        }
        self.active_modifiers.clear()
        self.active_dots.clear()
        self.active_statuses.clear()
        self.status_immunities.clear()
        self.pending_charges.clear()

def load_skills_from_json(json_path: str) -> Dict[str, Skill]:
    with open(json_path, 'r') as file:
        raw_data = json.load(file)
    skills_db = {}
    for key, data in raw_data.items():
        try:
            type_enum = SkillType(data["type"])
        except ValueError:
            type_enum = SkillType.PASSIVE
        skills_db[key] = Skill(
            name=data["name"],
            skill_type=type_enum,
            activation_chance=data["activation_chance"],
            rage_cost=data.get("rage_cost", 0),
            effects=data.get("effects", [])
        )
    return skills_db

def load_heroes_from_json(json_path: str, skills_db: Dict[str, Skill]) -> Dict[str, Hero]:
    with open(json_path, 'r') as file:
        raw_data = json.load(file)
    heroes_db = {}
    for key, data in raw_data.items():
        military_enum = Military(data["military"])
        unit_types_enum = [UnitType(ut) for ut in data["unit_types"]]
        hero_skills = {}

        # Slot unik hero (umumnya commander/signature).
        for skill_slot, skill_id in data.get("default_skills", {}).items():
            if skill_slot.startswith("custom_"):
                continue
            if skill_id in skills_db:
                hero_skills[skill_slot] = skills_db[skill_id]

        # Skill umum lintas hero.
        for index, skill_id in enumerate(data.get("custom_skills", []), start=1):
            if skill_id in skills_db:
                hero_skills[f"custom_{index}"] = skills_db[skill_id]

        # Backward compatibility untuk format lama yang masih menaruh custom di default_skills.
        legacy_custom_index = len(data.get("custom_skills", [])) + 1
        for skill_slot, skill_id in data.get("default_skills", {}).items():
            if not skill_slot.startswith("custom_"):
                continue
            if skill_id in skills_db:
                hero_skills[f"custom_{legacy_custom_index}"] = skills_db[skill_id]
                legacy_custom_index += 1

        heroes_db[key] = Hero(
            name=data["name"],
            military=military_enum,
            unit_types=unit_types_enum,
            base_stats=data["base_stats"],
            growth_stats=data.get("growth_stats", {}),
            skills=hero_skills
        )
    return heroes_db


def load_templates_from_json(json_path: str | Path) -> dict:
    try:
        with open(json_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Warning: Template file not found at {json_path}")
        return {}

@dataclass
class GameData:
    skills: Dict[str, Skill]
    heroes: Dict[str, Hero]
    templates: dict

    @classmethod
    def load_from_files(cls, skills_path: Path | str, heroes_path: Path | str, templates_path: Path | str) -> "GameData":
        skills_db = load_skills_from_json(skills_path)
        heroes_db = load_heroes_from_json(heroes_path, skills_db)
        templates_db = load_templates_from_json(templates_path)
        return cls(skills=skills_db, heroes=heroes_db, templates=templates_db)


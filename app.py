import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REQUESTS_FILE = DATA_DIR / "requests.json"
USERS_FILE = DATA_DIR / "users.json"
XBOX_PROOF_UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "xbox-proofs"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

DISCORD_HEADERS = {
    "User-Agent": "ThunderBuddiesStudiosOAuth/1.0 (+https://fleettest-production.up.railway.app)",
    "Accept": "application/json",
}


MODULES = [
    {
        "id": "faction",
        "title": "Custom faction or unit identity",
        "prompt": "Uniforms, insignia, ranks, patches, role structure, and identity rules.",
        "base": 14,
        "risk": 4,
    },
    {
        "id": "weapons",
        "title": "Weapons, attachments, or ballistics",
        "prompt": "New weapon configs, attachment compatibility, recoil tuning, ammo behavior, or arsenals.",
        "base": 22,
        "risk": 12,
    },
    {
        "id": "vehicles",
        "title": "Vehicles or vehicle variants",
        "prompt": "Textures, loadouts, physics tuning, seats, turrets, cargo behavior, or damage setups.",
        "base": 28,
        "risk": 15,
    },
    {
        "id": "terrain",
        "title": "Terrain, bases, or world composition",
        "prompt": "Forward bases, checkpoints, training ranges, roads, lighting, props, or map edits.",
        "base": 26,
        "risk": 10,
    },
    {
        "id": "ai",
        "title": "AI behavior or mission systems",
        "prompt": "Patrol logic, objectives, spawns, reinforcements, scripts, or game mode behavior.",
        "base": 30,
        "risk": 18,
    },
    {
        "id": "ui",
        "title": "UI, menus, or player workflow",
        "prompt": "Custom screens, role selection, interaction flows, inventory helpers, or admin tools.",
        "base": 20,
        "risk": 8,
    },
    {
        "id": "persistence",
        "title": "Progression or persistence",
        "prompt": "Saved loadouts, player stats, economy, unlocks, ranks, or server-side records.",
        "base": 34,
        "risk": 22,
    },
    {
        "id": "compatibility",
        "title": "Compatibility with existing mods",
        "prompt": "Dependencies, conflict prevention, load order, repacks, or integration with a mod list.",
        "base": 18,
        "risk": 14,
    },
]

BUILD_OPTION_GROUPS = [
    {
        "id": "content",
        "title": "Content & Identity",
        "options": [
            {"id": "custom_faction", "label": "Custom faction", "points": 14},
            {"id": "uniforms_patches", "label": "Uniforms, patches, insignia", "points": 12},
            {"id": "ranks_roles", "label": "Ranks, roles, unit structure", "points": 8},
            {"id": "arsenal_setup", "label": "Arsenal/loadout setup", "points": 10},
            {"id": "localization", "label": "String/localization entries", "points": 6},
        ],
    },
    {
        "id": "gameplay",
        "title": "Gameplay Systems",
        "options": [
            {"id": "scenario_flow", "label": "Scenario/game mode flow", "points": 18},
            {"id": "objectives_tasks", "label": "Objectives and tasks", "points": 14},
            {"id": "ai_spawns", "label": "AI spawns and patrols", "points": 20},
            {"id": "respawn_rules", "label": "Respawn rules", "points": 12},
            {"id": "admin_tools", "label": "Admin tools", "points": 18},
            {"id": "persistence", "label": "Progression or persistence", "points": 30},
        ],
    },
    {
        "id": "assets",
        "title": "Assets & Vehicles",
        "options": [
            {"id": "weapon_configs", "label": "Weapons or attachment configs", "points": 22},
            {"id": "vehicle_variants", "label": "Vehicle variants", "points": 26},
            {"id": "vehicle_physics", "label": "Vehicle physics/tuning", "points": 24},
            {"id": "textures_materials", "label": "Textures and materials", "points": 14},
            {"id": "animations", "label": "Animation work", "points": 28},
            {"id": "particles", "label": "Particles and effects", "points": 16},
            {"id": "audio", "label": "Audio editor work", "points": 16},
        ],
    },
    {
        "id": "world",
        "title": "World & Terrain",
        "options": [
            {"id": "world_editor", "label": "World Editor composition", "points": 20},
            {"id": "bases_checkpoints", "label": "Bases/checkpoints", "points": 16},
            {"id": "terrain_generation", "label": "Terrain generator work", "points": 32},
            {"id": "lighting_weather", "label": "Lighting/time/weather setup", "points": 12},
            {"id": "props_prefabs", "label": "Props and prefab placement", "points": 14},
        ],
    },
    {
        "id": "technical",
        "title": "Technical Workbench",
        "options": [
            {"id": "script_editor", "label": "Script Editor work", "points": 24},
            {"id": "resource_manager", "label": "Resource Manager setup", "points": 10},
            {"id": "behavior_editor", "label": "Behavior Editor nodes", "points": 22},
            {"id": "procedural_animation", "label": "Procedural animation", "points": 28},
            {"id": "workbench_links", "label": "Workbench links/tracing", "points": 8},
            {"id": "dependency_setup", "label": "Dependency setup", "points": 12},
        ],
    },
    {
        "id": "delivery",
        "title": "Testing & Delivery",
        "options": [
            {"id": "console_testing", "label": "Console/client testing", "points": 16},
            {"id": "multiplayer_qa", "label": "Multiplayer QA", "points": 22},
            {"id": "conflict_testing", "label": "Dependency conflict testing", "points": 18},
            {"id": "packaging_publish", "label": "Packaging/publishing", "points": 14},
            {"id": "documentation", "label": "Client documentation", "points": 8},
        ],
    },
]

BUILD_OPTION_GROUPS.extend(
    [
        {
            "id": "terrain_detail",
            "title": "Terrain Production",
            "options": [
                {"id": "terrain_research", "label": "Terrain research/reference pass", "points": 10},
                {"id": "heightfield_import", "label": "Heightfield import", "points": 20},
                {"id": "satmap_masks", "label": "Satellite map and surface masks", "points": 22},
                {"id": "surface_blending", "label": "Surface blending/block planning", "points": 18},
                {"id": "object_layers", "label": "Object layer organization", "points": 14},
                {"id": "settlement_layers", "label": "Settlement/village layers", "points": 18},
                {"id": "toponym_layers", "label": "Toponyms/place names", "points": 10},
                {"id": "road_network", "label": "Road network", "points": 24},
                {"id": "forest_generators", "label": "Forest generators", "points": 22},
                {"id": "water_bodies", "label": "Water bodies", "points": 20},
                {"id": "rivers", "label": "Rivers", "points": 24},
                {"id": "powerlines", "label": "Powerlines", "points": 14},
                {"id": "shorelines", "label": "Shoreline pass", "points": 18},
                {"id": "seabed_prep", "label": "Seabed landscape preparation", "points": 18},
                {"id": "terrain_performance", "label": "Terrain performance pass", "points": 26},
                {"id": "terrain_iteration_repo", "label": "Version-controlled terrain workflow", "points": 10},
            ],
        },
        {
            "id": "scenario_framework",
            "title": "Scenario Framework",
            "options": [
                {"id": "scenario_setup", "label": "Scenario Framework setup", "points": 18},
                {"id": "sf_components", "label": "Framework components", "points": 16},
                {"id": "sf_plugins", "label": "Framework plugins", "points": 16},
                {"id": "sf_logic", "label": "Scenario logic", "points": 20},
                {"id": "sf_getters", "label": "Getters/data lookup", "points": 12},
                {"id": "sf_actions", "label": "Actions/interactions", "points": 18},
                {"id": "sf_dynamic_spawn", "label": "Dynamic spawn/despawn", "points": 24},
                {"id": "sf_save_load", "label": "Save/load behavior", "points": 26},
                {"id": "gm_integration", "label": "Game Master integration", "points": 16},
                {"id": "conflict_integration", "label": "Conflict mode integration", "points": 18},
                {"id": "scenario_samples", "label": "Sample/reference scenario setup", "points": 10},
            ],
        },
        {
            "id": "ui_layouts",
            "title": "UI Layouts & Widgets",
            "options": [
                {"id": "hud_display", "label": "HUD/display layout", "points": 18},
                {"id": "menu_layout", "label": "Menu layout", "points": 20},
                {"id": "dialog_layout", "label": "Dialog/popup layout", "points": 18},
                {"id": "widget_buttons", "label": "Buttons and controls", "points": 12},
                {"id": "widget_scrollbars", "label": "Scrollbars/lists", "points": 12},
                {"id": "inventory_ui", "label": "Inventory-style UI", "points": 24},
                {"id": "field_manual_ui", "label": "Field manual/info UI", "points": 16},
                {"id": "chimera_menu_preset", "label": "Chimera menu preset scripting", "points": 18},
                {"id": "ui_script_class", "label": "UI script class", "points": 20},
                {"id": "ui_preload_persistence", "label": "UI preload/persistence setup", "points": 12},
            ],
        },
        {
            "id": "asset_pipeline",
            "title": "Asset Pipeline",
            "options": [
                {"id": "prefabs_basics", "label": "Prefab setup", "points": 14},
                {"id": "data_overrides", "label": "Data modding/overrides", "points": 18},
                {"id": "weapon_asset_prep", "label": "Weapon mesh preparation", "points": 20},
                {"id": "weapon_prefab_config", "label": "Weapon prefab configuration", "points": 26},
                {"id": "weapon_sockets", "label": "Weapon sockets/attachments", "points": 22},
                {"id": "weapon_skeleton", "label": "Weapon skeleton setup", "points": 24},
                {"id": "weapon_animation", "label": "Weapon animation", "points": 28},
                {"id": "weapon_sounds", "label": "Weapon sounds", "points": 16},
                {"id": "vehicle_sim_params", "label": "Vehicle simulation parameters", "points": 24},
                {"id": "vehicle_turrets", "label": "Vehicle turrets", "points": 28},
                {"id": "character_prefabs", "label": "Character prefabs", "points": 20},
                {"id": "gear_retextures", "label": "Gear retextures", "points": 14},
                {"id": "prop_import", "label": "Prop import", "points": 18},
                {"id": "colliders", "label": "Collider setup", "points": 18},
                {"id": "custom_actions", "label": "Custom actions", "points": 20},
                {"id": "fbx_orientation", "label": "FBX orientation/import cleanup", "points": 12},
            ],
        },
        {
            "id": "scripting_deep",
            "title": "Scripting & Modules",
            "options": [
                {"id": "script_folder_structure", "label": "Script folder structure", "points": 10},
                {"id": "modder_tag_conflicts", "label": "Modder tag/class conflict prevention", "points": 8},
                {"id": "core_module", "label": "Core module scripting", "points": 22},
                {"id": "gamelib_module", "label": "GameLib module scripting", "points": 22},
                {"id": "game_module", "label": "Game module scripting", "points": 24},
                {"id": "workbench_module", "label": "Workbench module scripting", "points": 22},
                {"id": "workbenchgame_module", "label": "WorkbenchGame module scripting", "points": 22},
                {"id": "scoring_changes", "label": "Scoring/rules changes", "points": 18},
                {"id": "script_wizard", "label": "Script Wizard setup", "points": 8},
                {"id": "debug_logs", "label": "Debug/logging pass", "points": 10},
                {"id": "enfusion_trace_hooks", "label": "Enfusion tracing hooks", "points": 18},
            ],
        },
        {
            "id": "workbench_tools",
            "title": "Workbench Tools",
            "options": [
                {"id": "resource_browser", "label": "Resource Browser work", "points": 10},
                {"id": "resource_options", "label": "Resource Manager options", "points": 10},
                {"id": "world_editor_plugins", "label": "World Editor plugins", "points": 18},
                {"id": "world_editor_tools", "label": "World Editor tools", "points": 18},
                {"id": "animation_state_machine", "label": "Animation state machine", "points": 24},
                {"id": "animation_human_vars", "label": "Human animation variables", "points": 18},
                {"id": "vehicle_action_commands", "label": "Vehicle action commands", "points": 22},
                {"id": "audio_variables", "label": "Audio variables", "points": 14},
                {"id": "audio_directivity", "label": "Audio directivity", "points": 16},
                {"id": "audio_dsp_nodes", "label": "Audio DSP nodes", "points": 18},
                {"id": "behavior_nodes", "label": "Behavior Editor nodes", "points": 22},
                {"id": "string_tables", "label": "String tables", "points": 8},
                {"id": "procedural_nodes", "label": "Procedural animation nodes", "points": 24},
                {"id": "workbench_metadata", "label": "Workbench metadata", "points": 8},
                {"id": "enfusion_protocol_links", "label": "enfusion:// Workbench links", "points": 8},
            ],
        },
        {
            "id": "dependency_management",
            "title": "Dependency Management",
            "options": [
                {"id": "scan_projects", "label": "Scan existing addon projects", "points": 8},
                {"id": "dependency_tree", "label": "Dependency tree review", "points": 16},
                {"id": "dependency_presets", "label": "Workbench presets", "points": 10},
                {"id": "missing_guid_lookup", "label": "Missing GUID lookup", "points": 12},
                {"id": "dependency_conflict_log", "label": "Conflict log review", "points": 16},
                {"id": "experimental_branch", "label": "Experimental branch compatibility", "points": 18},
                {"id": "clean_mod_cache", "label": "Clean-state mod cache test", "points": 10},
                {"id": "console_dependency_test", "label": "Console dependency install test", "points": 16},
            ],
        },
    ]
)

WORKSHOP_FALLBACK_DEPENDENCIES = [
    {"id": "where_am_i", "label": "Where Am I", "author": "ValterB", "points": 4},
    {"id": "project_redline_uh60", "label": "Project Redline - UH-60", "author": "Ralian", "points": 14},
    {"id": "better_hits_effects", "label": "BetterHitsEffects -ABANDONED-", "author": "Ashyl", "points": 8},
    {"id": "better_tracers", "label": "BetterTracers -ABANDONED-", "author": "Ashyl", "points": 8},
    {"id": "project_redline_core", "label": "Project Redline - Core", "author": "Redline Mod Team", "points": 12},
    {"id": "ris_laser_attachments", "label": "RIS Laser Attachments", "author": "ceo_of_bacon", "points": 8},
    {"id": "better_muzzle_flash", "label": "BetterMuzzleFlash -ABANDONED-", "author": "Ashyl", "points": 8},
    {"id": "night_vision_system", "label": "Night Vision System", "author": "Greg3d_fr", "points": 10},
    {"id": "stryker", "label": "STRYKER", "author": "TheSpaceStrider", "points": 14},
    {"id": "rhs_status_quo", "label": "RHS - Status Quo", "author": "Red Hammer Studios", "points": 18},
    {"id": "ah64d_apache", "label": "AH-64D Apache", "author": "TheSpaceStrider", "points": 16},
    {"id": "sample_mod_new_car", "label": "Sample Mod - New Car", "author": "Bohemia Interactive", "points": 6},
    {"id": "jltv", "label": "Joint Light Tactical Vehicle", "author": "TheSpaceStrider", "points": 14},
    {"id": "task_force_mattock_weapons", "label": "Task Force Mattock Weapons", "author": "TheAussieMerc", "points": 14},
    {"id": "m1_abrams", "label": "M1 Abrams", "author": "TheSpaceStrider", "points": 16},
    {"id": "m110_dmr", "label": "M110 DMR", "author": "ceo_of_bacon", "points": 10},
    {"id": "barrett_m82", "label": "Barrett M82", "author": "ceo_of_bacon", "points": 10},
    {"id": "game_master_fx", "label": "Game Master FX", "author": "ceo_of_bacon", "points": 8},
    {"id": "sample_mod_modded_weapon", "label": "Sample Mod - Modded Weapon", "author": "Bohemia Interactive", "points": 6},
    {"id": "bmp3_ifv", "label": "BMP-3 IFV", "author": "TheSpaceStrider", "points": 16},
    {"id": "kunarprovince", "label": "KunarProvince", "author": "KIOK", "points": 18},
    {"id": "better_explosives", "label": "BetterExplosives 2.0 Outdated", "author": "Ashyl", "points": 8},
    {"id": "vergys_custom_clothing", "label": "Vergys Custom Clothing", "author": "Vergyy", "points": 12},
    {"id": "sample_mod_new_weapon", "label": "Sample Mod - New Weapon", "author": "Bohemia Interactive", "points": 6},
    {"id": "everon_life", "label": "Everon Life", "author": "Everon Life Team", "points": 18},
    {"id": "shrapnel", "label": "Shrapnel 2.0", "author": "Ashyl", "points": 8},
    {"id": "bacon_suppressors", "label": "Bacon Suppressors", "author": "ceo_of_bacon", "points": 8},
    {"id": "rhib", "label": "RHIB", "author": "TheSpaceStrider", "points": 14},
    {"id": "task_force_mattock_uniforms", "label": "Task Force Mattock Uniforms", "author": "TheAussieMerc", "points": 12},
    {"id": "sample_mod_modded_car", "label": "Sample Mod - Modded Car", "author": "Bohemia Interactive", "points": 6},
    {"id": "sample_mod_workbench_plugin", "label": "Sample Mod - Workbench Plugin", "author": "Bohemia Interactive", "points": 6},
    {"id": "sample_mod_new_faction", "label": "Sample Mod - New Faction", "author": "Bohemia Interactive", "points": 6},
    {"id": "sample_mod_modded_script", "label": "Sample Mod - Modded Script", "author": "Bohemia Interactive", "points": 6},
    {"id": "zeliks_character", "label": "Zeliks Character", "author": "zelik", "points": 10},
    {"id": "m249_scope_rails", "label": "M249 Scope Rails", "author": "ceo_of_bacon", "points": 8},
    {"id": "better_sounds", "label": "BetterSounds 4.0 Alpha", "author": "Ashyl", "points": 10},
    {"id": "sample_mod_new_prop", "label": "Sample Mod - New Prop", "author": "Bohemia Interactive", "points": 6},
    {"id": "dark_raider_vehicle_pack", "label": "Dark Raider Vehicle Pack", "author": "TheSpaceStrider", "points": 16},
    {"id": "game_master_enhanced", "label": "Game Master Enhanced", "author": "GME Mod Team", "points": 12},
    {"id": "overthrow", "label": "Overthrow", "author": "Aaron Static", "points": 18},
    {"id": "british_armed_forces_vehicles", "label": "British Armed Forces Vehicles", "author": "TheSpaceStrider", "points": 16},
    {"id": "sample_mod_main_addon", "label": "Sample Mod - Main Addon", "author": "Bohemia Interactive", "points": 6},
    {"id": "hmas_adelaide", "label": "HMAS Adelaide", "author": "TheSpaceStrider", "points": 16},
    {"id": "m17_pistol", "label": "M17 Pistol", "author": "ceo_of_bacon", "points": 8},
    {"id": "cs_forces", "label": "CS Forces", "author": "ViktorTroska", "points": 12},
    {"id": "third_ranger_vehicle_pack", "label": "3rd Ranger Vehicle Pack", "author": "TheSpaceStrider", "points": 16},
    {"id": "better_ammo", "label": "BetterAmmo", "author": "Ashyl", "points": 8},
    {"id": "cz_scorpion_evo3_smg", "label": "CZ Scorpion EVO3 SMG", "author": "ceo_of_bacon", "points": 10},
    {"id": "bon_action_animations", "label": "Bon Action Animations", "author": "TheBonBon", "points": 12},
    {"id": "cougar_mrap", "label": "Cougar MRAP", "author": "TheSpaceStrider", "points": 16},
    {"id": "dog_gear", "label": "dog_Gear", "author": "thedog88", "points": 12},
    {"id": "sample_mod_new_character", "label": "Sample Mod - New Character", "author": "Bohemia Interactive", "points": 6},
    {"id": "t72_main_battle_tank", "label": "T-72 Main Battle Tank", "author": "TheSpaceStrider", "points": 16},
    {"id": "enfusion_database_framework", "label": "Enfusion Database Framework", "author": "Arkensor", "points": 12},
    {"id": "hmmwv_variants", "label": "HmmwvVariants", "author": "KIOK", "points": 16},
    {"id": "m270_mlrs", "label": "M270 MLRS", "author": "TheSpaceStrider", "points": 16},
    {"id": "enfusion_persistence_framework", "label": "Enfusion Persistence Framework", "author": "Arkensor", "points": 12},
    {"id": "zimnitrita", "label": "Zimnitrita", "author": "Casseburne", "points": 18},
    {"id": "first_ranger_vehicle_pack", "label": "1st Ranger Vehicle Pack", "author": "TheSpaceStrider", "points": 16},
    {"id": "zbk", "label": "ZBK", "author": "LaFrenchTouche", "points": 14},
    {"id": "gm_persistent_loadouts", "label": "GM Persistent Loadouts", "author": "ceo_of_bacon", "points": 10},
    {"id": "worthy_islands", "label": "Worthy Islands", "author": "Chewie_", "points": 18},
    {"id": "spacecore", "label": "SpaceCore", "author": "TheSpaceStrider", "points": 12},
    {"id": "tf_mattock_blufor_opfor", "label": "TF Mattock BLUFOR OPFOR", "author": "TheAussieMerc", "points": 14},
]
WORKSHOP_DEPENDENCIES = WORKSHOP_FALLBACK_DEPENDENCIES[:64]

PHASES = [
    "Request received",
    "Design review",
    "Work estimate",
    "Production",
    "Internal QA",
    "Client review",
    "Packaged delivery",
]

PRIORITIES = ["Backlog", "Normal", "High", "Critical"]
PROJECT_TYPES = ["Client mod", "Internal tool", "Asset pack", "Compatibility patch", "Research spike"]
STUDIO_TABS = ["Command", "Projects", "Pipeline", "Clients", "Complexity", "Freelance Pool", "Settings", "Admin"]
CLIENT_TABS = ["Overview", "Requests", "New Build", "Donate", "Account"]
ROLES = ["customer", "developer", "moderator", "tester", "staff", "admin"]
STAFF_ROLES = {"developer", "moderator", "tester", "staff", "admin"}
ROLE_DASHBOARDS = {
    "admin": {
        "title": "Admin Command",
        "headline": "Full studio oversight",
        "summary": "Control account access, partner studios, production economy, requests, staff time, and studio-wide operations.",
        "actions": ["Permissions", "Production economy", "Suspensions", "Network health"],
    },
    "developer": {
        "title": "Developer Console",
        "headline": "Build work and time tracing",
        "summary": "Clock into assigned projects, track Enfusion work, review dependencies, and claim eligible freelance pool items.",
        "actions": ["Project clock", "Build notes", "Freelance pool", "Task checklist"],
    },
    "moderator": {
        "title": "Moderator Desk",
        "headline": "Queue and client safety",
        "summary": "Review intake quality, watch client-facing updates, triage over-lane tickets, and help keep the request flow clean.",
        "actions": ["Queue review", "Client notes", "Risk flags", "Pool review"],
    },
    "tester": {
        "title": "QA Bench",
        "headline": "Testing and release confidence",
        "summary": "Focus on phase progress, checklist completion, multiplayer QA, console checks, and ready-for-review builds.",
        "actions": ["QA checklist", "Phase map", "Console testing", "Release notes"],
    },
    "staff": {
        "title": "General Staff Hub",
        "headline": "Studio support lane",
        "summary": "Clock studio time, help with intake support, review assigned work, and keep internal operations moving.",
        "actions": ["Studio clock", "Support queue", "Assignments", "Staff stats"],
    },
}
POINT_DONATION_RATE = 1.25
POINT_CASH_RATE = 3.15
POINTS_PER_HOUR = 3.4
DEV_HOURLY_RATE = 85
GAMEPLAY_POINT_RATE = 7.5
ARMA_REFORGER_STEAM_APP_ID = 1874880
STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
STEAM_OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
XBOX_REFORGER_PLAYTIME_URL = os.environ.get("XBOX_REFORGER_PLAYTIME_URL", "").strip()
XBOX_REFORGER_TITLE_ID = os.environ.get("XBOX_REFORGER_TITLE_ID", "").strip()
XBOX_API_KEY = os.environ.get("XBOX_API_KEY", "").strip()
GOFUNDME_CHARITY_SEARCH_URL = "https://www.gofundme.com/s?q="
WORKSHOP_BASE_URL = "https://reforger.armaplatform.com/workshop"
WORKSHOP_PAGE_SIZE = 16
WORKSHOP_CACHE_SECONDS = 60 * 20
WORKSHOP_CACHE = {}
FEATURED_CHARITIES = sorted(
    [
        {"id": "aclu_foundation", "name": "ACLU Foundation", "cause": "Civil liberties", "url": "https://www.aclu.org/"},
        {"id": "against_malaria_foundation", "name": "Against Malaria Foundation", "cause": "Global health", "url": "https://www.againstmalaria.com/"},
        {"id": "alzheimers_association", "name": "Alzheimer's Association", "cause": "Alzheimer's care and research", "url": "https://www.alz.org/"},
        {"id": "american_cancer_society", "name": "American Cancer Society", "cause": "Cancer research and patient support", "url": "https://www.cancer.org/"},
        {"id": "american_heart_association", "name": "American Heart Association", "cause": "Heart health and research", "url": "https://www.heart.org/"},
        {"id": "aspca", "name": "ASPCA", "cause": "Animal rescue and welfare", "url": "https://www.aspca.org/"},
        {"id": "best_friends_animal_society", "name": "Best Friends Animal Society", "cause": "Animal rescue and adoption", "url": "https://bestfriends.org/"},
        {"id": "big_brothers_big_sisters", "name": "Big Brothers Big Sisters of America", "cause": "Youth mentorship", "url": "https://www.bbbs.org/"},
        {"id": "black_girls_code", "name": "Black Girls Code", "cause": "STEM education", "url": "https://www.blackgirlscode.com/"},
        {"id": "boys_girls_clubs", "name": "Boys & Girls Clubs of America", "cause": "Youth development", "url": "https://www.bgca.org/"},
        {"id": "breakthrough_t1d", "name": "Breakthrough T1D", "cause": "Type 1 diabetes research", "url": "https://www.breakthrought1d.org/"},
        {"id": "care", "name": "CARE", "cause": "Global poverty and humanitarian relief", "url": "https://www.care.org/"},
        {"id": "charity_water", "name": "charity: water", "cause": "Clean water access", "url": "https://www.charitywater.org/"},
        {"id": "code_org", "name": "Code.org", "cause": "Computer science education", "url": "https://code.org/"},
        {"id": "covenant_house", "name": "Covenant House", "cause": "Youth homelessness", "url": "https://www.covenanthouse.org/"},
        {"id": "direct_relief", "name": "Direct Relief", "cause": "Medical aid and disaster relief", "url": "https://www.directrelief.org/"},
        {"id": "doctors_without_borders", "name": "Doctors Without Borders", "cause": "Emergency medical relief", "url": "https://www.doctorswithoutborders.org/"},
        {"id": "donorschoose", "name": "DonorsChoose", "cause": "Classroom funding", "url": "https://www.donorschoose.org/"},
        {"id": "eff", "name": "Electronic Frontier Foundation", "cause": "Digital rights", "url": "https://www.eff.org/"},
        {"id": "enterprise_community_partners", "name": "Enterprise Community Partners", "cause": "Affordable housing", "url": "https://www.enterprisecommunity.org/"},
        {"id": "feeding_america", "name": "Feeding America", "cause": "Hunger relief", "url": "https://www.feedingamerica.org/"},
        {"id": "fisher_house_foundation", "name": "Fisher House Foundation", "cause": "Military and veteran family housing", "url": "https://www.fisherhouse.org/"},
        {"id": "food_for_the_poor", "name": "Food For The Poor", "cause": "Poverty relief", "url": "https://foodforthepoor.org/"},
        {"id": "girls_who_code", "name": "Girls Who Code", "cause": "STEM education", "url": "https://girlswhocode.com/"},
        {"id": "globalgiving", "name": "GlobalGiving", "cause": "Grassroots nonprofit funding", "url": "https://www.globalgiving.org/"},
        {"id": "gofundme_org", "name": "GoFundMe.org", "cause": "Crisis relief and community support", "url": "https://www.gofundme.org/"},
        {"id": "habitat_for_humanity", "name": "Habitat for Humanity", "cause": "Housing and neighborhood development", "url": "https://www.habitat.org/"},
        {"id": "heart_to_heart_international", "name": "Heart to Heart International", "cause": "Humanitarian medical relief", "url": "https://www.hearttoheart.org/"},
        {"id": "heifer_international", "name": "Heifer International", "cause": "Food security and livelihoods", "url": "https://www.heifer.org/"},
        {"id": "human_rights_watch", "name": "Human Rights Watch", "cause": "Human rights", "url": "https://www.hrw.org/"},
        {"id": "international_medical_corps", "name": "International Medical Corps", "cause": "Emergency medical relief", "url": "https://internationalmedicalcorps.org/"},
        {"id": "international_rescue_committee", "name": "International Rescue Committee", "cause": "Refugee and crisis response", "url": "https://www.rescue.org/"},
        {"id": "junior_achievement", "name": "Junior Achievement USA", "cause": "Youth financial literacy", "url": "https://jausa.ja.org/"},
        {"id": "khan_academy", "name": "Khan Academy", "cause": "Free education", "url": "https://www.khanacademy.org/"},
        {"id": "leukemia_lymphoma_society", "name": "Leukemia & Lymphoma Society", "cause": "Blood cancer research", "url": "https://www.lls.org/"},
        {"id": "make_a_wish", "name": "Make-A-Wish America", "cause": "Critical illness support for children", "url": "https://wish.org/"},
        {"id": "map_international", "name": "MAP International", "cause": "Medicine and health access", "url": "https://www.map.org/"},
        {"id": "meals_on_wheels", "name": "Meals on Wheels America", "cause": "Senior hunger relief", "url": "https://www.mealsonwheelsamerica.org/"},
        {"id": "mental_health_america", "name": "Mental Health America", "cause": "Mental health advocacy", "url": "https://mhanational.org/"},
        {"id": "mercy_corps", "name": "Mercy Corps", "cause": "Humanitarian aid and recovery", "url": "https://www.mercycorps.org/"},
        {"id": "muscular_dystrophy_association", "name": "Muscular Dystrophy Association", "cause": "Neuromuscular disease research", "url": "https://www.mda.org/"},
        {"id": "naacp_ldf", "name": "NAACP Legal Defense Fund", "cause": "Racial justice", "url": "https://naacpldf.org/"},
        {"id": "nami", "name": "National Alliance on Mental Illness", "cause": "Mental health support", "url": "https://www.nami.org/"},
        {"id": "national_ms_society", "name": "National Multiple Sclerosis Society", "cause": "Multiple sclerosis research and support", "url": "https://www.nationalmssociety.org/"},
        {"id": "nature_conservancy", "name": "The Nature Conservancy", "cause": "Land and water conservation", "url": "https://www.nature.org/"},
        {"id": "oceana", "name": "Oceana", "cause": "Ocean conservation", "url": "https://oceana.org/"},
        {"id": "operation_homefront", "name": "Operation Homefront", "cause": "Military family support", "url": "https://operationhomefront.org/"},
        {"id": "oxfam_america", "name": "Oxfam America", "cause": "Poverty and disaster response", "url": "https://www.oxfamamerica.org/"},
        {"id": "parkinsons_foundation", "name": "Parkinson's Foundation", "cause": "Parkinson's care and research", "url": "https://www.parkinson.org/"},
        {"id": "partners_in_health", "name": "Partners In Health", "cause": "Global health equity", "url": "https://www.pih.org/"},
        {"id": "planned_parenthood", "name": "Planned Parenthood Federation of America", "cause": "Reproductive health care", "url": "https://www.plannedparenthood.org/"},
        {"id": "project_hope", "name": "Project HOPE", "cause": "Global health and disaster response", "url": "https://www.projecthope.org/"},
        {"id": "rainforest_trust", "name": "Rainforest Trust", "cause": "Rainforest conservation", "url": "https://www.rainforesttrust.org/"},
        {"id": "red_cross", "name": "American Red Cross", "cause": "Disaster relief and blood services", "url": "https://www.redcross.org/"},
        {"id": "rmhc", "name": "Ronald McDonald House Charities", "cause": "Family support during pediatric care", "url": "https://rmhc.org/"},
        {"id": "room_to_read", "name": "Room to Read", "cause": "Literacy and girls' education", "url": "https://www.roomtoread.org/"},
        {"id": "rotary_foundation", "name": "The Rotary Foundation of Rotary International", "cause": "Global grants and community projects", "url": "https://www.rotary.org/en/donate"},
        {"id": "save_the_children", "name": "Save the Children", "cause": "Child protection and relief", "url": "https://www.savethechildren.org/us/"},
        {"id": "sierra_club_foundation", "name": "Sierra Club Foundation", "cause": "Environmental protection", "url": "https://www.sierraclubfoundation.org/"},
        {"id": "special_olympics", "name": "Special Olympics", "cause": "Inclusive sports", "url": "https://www.specialolympics.org/"},
        {"id": "st_jude", "name": "St. Jude Children's Research Hospital", "cause": "Pediatric cancer research", "url": "https://www.stjude.org/"},
        {"id": "susan_g_komen", "name": "Susan G. Komen", "cause": "Breast cancer research and support", "url": "https://www.komen.org/"},
        {"id": "team_rubicon", "name": "Team Rubicon", "cause": "Disaster response", "url": "https://teamrubiconusa.org/"},
        {"id": "trevor_project", "name": "The Trevor Project", "cause": "LGBTQ youth crisis support", "url": "https://www.thetrevorproject.org/"},
        {"id": "tunnel_to_towers", "name": "Tunnel to Towers Foundation", "cause": "First responder and veteran support", "url": "https://t2t.org/"},
        {"id": "uncf", "name": "UNCF", "cause": "Scholarships and higher education", "url": "https://uncf.org/"},
        {"id": "unicef_usa", "name": "UNICEF USA", "cause": "Children's humanitarian aid", "url": "https://www.unicefusa.org/"},
        {"id": "water_org", "name": "Water.org", "cause": "Water and sanitation access", "url": "https://water.org/"},
        {"id": "wikimedia_foundation", "name": "Wikimedia Foundation", "cause": "Open knowledge", "url": "https://wikimediafoundation.org/"},
        {"id": "wounded_warrior_project", "name": "Wounded Warrior Project", "cause": "Veteran support", "url": "https://www.woundedwarriorproject.org/"},
        {"id": "world_central_kitchen", "name": "World Central Kitchen", "cause": "Disaster meal relief", "url": "https://wck.org/"},
        {"id": "world_resources_institute", "name": "World Resources Institute", "cause": "Climate and sustainability", "url": "https://www.wri.org/"},
        {"id": "world_vision", "name": "World Vision", "cause": "Child sponsorship and humanitarian aid", "url": "https://www.worldvision.org/"},
        {"id": "world_wildlife_fund", "name": "World Wildlife Fund", "cause": "Wildlife conservation", "url": "https://www.worldwildlife.org/"},
        {"id": "ymca", "name": "YMCA of the USA", "cause": "Youth and community support", "url": "https://www.ymca.org/"},
        {"id": "ywca", "name": "YWCA USA", "cause": "Women, racial justice, and community support", "url": "https://www.ywca.org/"},
    ],
    key=lambda item: item["name"],
)
TEST_ACCOUNTS = [
    {
        "username": "admin_test",
        "email": "admin@thunderbuddies.test",
        "password": "ThunderAdmin123!",
        "role": "admin",
        "studio_name": "Thunder Buddies Studios",
    },
    {
        "username": "client_test",
        "email": "client@thunderbuddies.test",
        "password": "ThunderClient123!",
        "role": "customer",
        "studio_name": "",
    },
    {
        "username": "tbs_dev_test",
        "email": "tbs.dev@thunderbuddies.test",
        "password": "ThunderDev123!",
        "role": "developer",
        "studio_name": "Thunder Buddies Studios",
    },
    {
        "username": "partner_dev_test",
        "email": "partner.dev@thunderbuddies.test",
        "password": "PartnerDev123!",
        "role": "developer",
        "studio_name": "Partner Studio Alpha",
    },
    {
        "username": "tester_test",
        "email": "tester@thunderbuddies.test",
        "password": "ThunderTester123!",
        "role": "tester",
        "studio_name": "Thunder Buddies Studios QA",
    },
    {
        "username": "moderator_test",
        "email": "moderator@thunderbuddies.test",
        "password": "ThunderMod123!",
        "role": "moderator",
        "studio_name": "Thunder Buddies Studios",
    },
    {
        "username": "staff_test",
        "email": "staff@thunderbuddies.test",
        "password": "ThunderStaff123!",
        "role": "staff",
        "studio_name": "Thunder Buddies Studios",
    },
]


def safe_dependency_id(value):
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:80] or f"workshop_{secrets.token_hex(4)}"


def dependency_points(label, author="", size_text="", rating=0):
    text = f"{label} {author}".lower()
    points = 6
    if any(term in text for term in ["framework", "persistence", "database", "core", "life", "overthrow"]):
        points += 6
    if any(term in text for term in ["vehicle", "tank", "ifv", "mrap", "apache", "uh-60", "rhib", "hmmwv", "mlrs"]):
        points += 8
    if any(term in text for term in ["weapon", "m82", "m110", "suppressor", "ammo", "scope", "rifle", "pistol", "smg"]):
        points += 4
    if any(term in text for term in ["terrain", "island", "province", "map", "anizay", "kunar"]):
        points += 10
    if "gb" in size_text.lower():
        points += 6
    if rating and rating < 85:
        points += 2
    return min(points, 22)


def parse_workshop_listing(html):
    mods = []
    anchor_pattern = re.compile(r'<a[^>]+href="(?P<href>/workshop/[^"]+)"[^>]*>(?P<body>.*?)</a>', re.I | re.S)
    for match in anchor_pattern.finditer(html):
        body = re.sub(r"<[^>]+>", " ", match.group("body"))
        text = " ".join(unescape(body).split())
        if " by " not in text or "%" not in text:
            continue
        details = re.match(r"(?P<size>.+?)\s+(?P<rating>\d+)\s*%\s+(?P<label>.+?)\s+by\s+(?P<author>.+)$", text)
        if not details:
            continue
        href = match.group("href")
        raw_id = href.rstrip("/").split("/")[-1].split("-")[0]
        label = details.group("label").strip()
        author = details.group("author").strip()
        rating = int(details.group("rating"))
        size_text = details.group("size").strip()
        mods.append(
            {
                "id": safe_dependency_id(raw_id or label),
                "workshop_id": raw_id,
                "label": label,
                "author": author,
                "points": dependency_points(label, author, size_text, rating),
                "rating": rating,
                "size": size_text,
                "source_url": f"{WORKSHOP_BASE_URL}/{raw_id}",
            }
        )
    return mods


def fallback_workshop_page(page=1):
    page = max(1, int(page or 1))
    start = (page - 1) * WORKSHOP_PAGE_SIZE
    end = start + WORKSHOP_PAGE_SIZE
    return WORKSHOP_FALLBACK_DEPENDENCIES[start:end]


def fetch_workshop_page(page=1):
    page = max(1, min(int(page or 1), 2277))
    cache_key = f"page:{page}"
    cached = WORKSHOP_CACHE.get(cache_key)
    if cached and time.time() - cached["created"] < WORKSHOP_CACHE_SECONDS:
        return cached["mods"]

    url = WORKSHOP_BASE_URL if page == 1 else f"{WORKSHOP_BASE_URL}?page={page}"
    request = Request(url, headers=DISCORD_HEADERS)
    try:
        with urlopen(request, timeout=8) as response:
            html = response.read().decode("utf-8", errors="replace")
        mods = parse_workshop_listing(html)
    except (HTTPError, URLError, TimeoutError, ValueError):
        mods = []

    if not mods:
        mods = fallback_workshop_page(page)

    WORKSHOP_CACHE[cache_key] = {"created": time.time(), "mods": mods}
    return mods


def workshop_dependencies_for_builder(pages=4):
    pages = max(1, min(int(pages or 1), 12))
    seen = set()
    mods = []
    for page in range(1, pages + 1):
        for mod in fetch_workshop_page(page):
            if mod["id"] in seen:
                continue
            seen.add(mod["id"])
            mods.append(mod)
    return mods


def workshop_initial_pages():
    try:
        return max(1, min(int(os.environ.get("WORKSHOP_INITIAL_PAGES", 4)), 12))
    except ValueError:
        return 4


def ensure_storage():
    DATA_DIR.mkdir(exist_ok=True)
    XBOX_PROOF_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not REQUESTS_FILE.exists():
        REQUESTS_FILE.write_text("[]", encoding="utf-8")
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")
    seed_test_accounts()


def seed_test_accounts():
    users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    existing = {user.get("email", "").lower(): user for user in users}
    changed = False

    for account in TEST_ACCOUNTS:
        existing_user = existing.get(account["email"])
        if existing_user:
            existing_user["username"] = account["username"]
            existing_user["role"] = account["role"]
            existing_user["studio_name"] = account.get("studio_name", "")
            existing_user.setdefault("prototype", True)
            changed = True
            continue
        users.append(
            {
                "id": f"usr_{secrets.token_hex(8)}",
                "username": account["username"],
                "email": account["email"],
                "role": account["role"],
                "password_hash": generate_password_hash(account["password"]),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": None,
                "avatar": None,
                "prototype": True,
                "account_points": 500 if account["role"] == "admin" else 120,
                "server_hours": 0,
                "supported_server_sessions": [],
                "point_transactions": [],
                "charity_donations": [],
                "suspended": False,
                "suspension_reason": "",
                "studio_name": account.get("studio_name", ""),
                "steam_id": "",
                "steam_name": "",
                "steam_avatar": "",
                "steam_playtime_minutes": 0,
                "steam_minutes_credited": 0,
                "steam_last_sync": "",
                "xbox_gamertag": "",
                "xbox_xuid": "",
                "xbox_playtime_minutes": 0,
                "xbox_minutes_credited": 0,
                "xbox_last_sync": "",
                "xbox_avatar": "",
                "xbox_access_token": "",
                "xbox_refresh_token": "",
                "xbox_token_expires_at": "",
                "xbox_playtime_submissions": [],
                "studio_time_entries": [],
            }
        )
        changed = True

    if changed:
        USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def load_requests():
    ensure_storage()
    records = json.loads(REQUESTS_FILE.read_text(encoding="utf-8"))
    normalized = [normalize_record(record) for record in records]
    if refresh_freelance_pool(normalized):
        save_requests(normalized)
    return normalized


def save_requests(records):
    ensure_storage()
    REQUESTS_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")


def normalize_user(user):
    user.setdefault("account_points", 0)
    user.setdefault("server_hours", 0)
    user.setdefault("supported_server_sessions", [])
    user.setdefault("point_spend_log", [])
    user.setdefault("point_transactions", [])
    user.setdefault("charity_donations", [])
    user.setdefault("suspended", False)
    user.setdefault("suspension_reason", "")
    user.setdefault("studio_name", "Thunder Buddies Studios" if user.get("role") == "admin" else "")
    user.setdefault("discord_id", "")
    user.setdefault("reforger_player_id", "")
    user.setdefault("steam_id", "")
    user.setdefault("steam_name", "")
    user.setdefault("steam_avatar", "")
    user.setdefault("steam_playtime_minutes", 0)
    user.setdefault("steam_minutes_credited", 0)
    user.setdefault("steam_last_sync", "")
    user.setdefault("xbox_gamertag", "")
    user.setdefault("xbox_xuid", "")
    user.setdefault("xbox_playtime_minutes", 0)
    user.setdefault("xbox_minutes_credited", 0)
    user.setdefault("xbox_last_sync", "")
    user.setdefault("xbox_avatar", "")
    user.setdefault("xbox_access_token", "")
    user.setdefault("xbox_refresh_token", "")
    user.setdefault("xbox_token_expires_at", "")
    user.setdefault("xbox_playtime_submissions", [])
    user.setdefault("studio_time_entries", [])
    existing_transaction_ids = {item.get("id") for item in user.get("point_transactions", [])}
    for credit in user.get("supported_server_sessions", []):
        transaction_id = f"credit_{credit.get('id', secrets.token_hex(5))}"
        if transaction_id in existing_transaction_ids:
            continue
        user["point_transactions"].append(
            {
                "id": transaction_id,
                "type": "credit",
                "source": credit.get("source", "steam"),
                "label": credit.get("server_name", "Steam Arma Reforger gameplay"),
                "points": millipoints(credit.get("points", 0)),
                "hours": credit.get("hours", 0),
                "reference": "",
                "note": credit.get("note", ""),
                "created_at": credit.get("recorded_at", ""),
            }
        )
    existing_transaction_ids = {item.get("id") for item in user.get("point_transactions", [])}
    for spend in user.get("point_spend_log", []):
        transaction_id = f"debit_{spend.get('id', secrets.token_hex(5))}"
        if transaction_id in existing_transaction_ids:
            continue
        user["point_transactions"].append(
            {
                "id": transaction_id,
                "type": "debit",
                "source": "request",
                "label": "Mod request submission",
                "points": millipoints(spend.get("points", 0)),
                "hours": 0,
                "reference": spend.get("reference", ""),
                "note": "Points spent from account balance.",
                "created_at": spend.get("created_at", ""),
            }
        )
    user["point_transactions"] = sorted(user["point_transactions"], key=lambda item: item.get("created_at", ""), reverse=True)
    return user


def load_users():
    ensure_storage()
    users = [normalize_user(user) for user in json.loads(USERS_FILE.read_text(encoding="utf-8"))]
    return users


def save_users(users):
    ensure_storage()
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def public_user(user):
    hidden = {"password_hash", "xbox_access_token", "xbox_refresh_token"}
    return {key: value for key, value in user.items() if key not in hidden}


def find_user(identifier):
    normalized = identifier.strip().lower()
    for user in load_users():
        if user.get("email", "").lower() == normalized or user.get("username", "").lower() == normalized:
            return user
    return None


def find_user_by_xbox_identity(xuid="", gamertag=""):
    normalized_xuid = (xuid or "").strip()
    normalized_gamertag = (gamertag or "").strip().lower()
    for user in load_users():
        if normalized_xuid and user.get("xbox_xuid", "").strip() == normalized_xuid:
            return user
        if normalized_gamertag and user.get("xbox_gamertag", "").strip().lower() == normalized_gamertag:
            return user
    return None


def create_user(username, email, password, role="customer"):
    users = load_users()
    user = {
        "id": f"usr_{secrets.token_hex(8)}",
        "username": username.strip(),
        "email": email.strip().lower(),
        "role": role,
        "password_hash": generate_password_hash(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
        "avatar": None,
        "prototype": False,
        "account_points": 0,
        "server_hours": 0,
        "supported_server_sessions": [],
        "point_spend_log": [],
        "point_transactions": [],
        "charity_donations": [],
        "suspended": False,
        "suspension_reason": "",
        "studio_name": "",
        "discord_id": "",
        "reforger_player_id": "",
        "steam_id": "",
        "steam_name": "",
        "steam_avatar": "",
        "steam_playtime_minutes": 0,
        "steam_minutes_credited": 0,
        "steam_last_sync": "",
        "xbox_gamertag": "",
        "xbox_xuid": "",
        "xbox_playtime_minutes": 0,
        "xbox_minutes_credited": 0,
        "xbox_last_sync": "",
        "xbox_avatar": "",
        "xbox_access_token": "",
        "xbox_refresh_token": "",
        "xbox_token_expires_at": "",
        "xbox_playtime_submissions": [],
        "studio_time_entries": [],
    }
    users.append(user)
    save_users(users)
    return user


def user_has_linked_game_account(user):
    return bool(user.get("steam_id") or user.get("xbox_gamertag") or user.get("xbox_xuid"))


def linked_reforger_hours(user):
    total_minutes = int(user.get("steam_playtime_minutes", 0) or 0) + int(user.get("xbox_playtime_minutes", 0) or 0)
    return millipoints(total_minutes / 60)


def safe_upload_filename(prefix, original_name):
    original_name = original_name or "upload.png"
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"
    return f"{prefix}_{secrets.token_hex(8)}{suffix}"


def access_code_allows(role, code):
    if role == "customer":
        return True
    env_name = "ADMIN_ACCESS_CODE" if role == "admin" else "DEVELOPER_ACCESS_CODE"
    expected = os.environ.get(env_name)
    if expected:
        return secrets.compare_digest(code or "", expected)
    fallback = "THUNDERADMIN" if role == "admin" else "THUNDERDEV"
    return secrets.compare_digest(code or "", fallback)


def fetch_steam_profile(steam_id):
    api_key = os.environ.get("STEAM_WEB_API_KEY", "")
    if not api_key:
        return {}
    params = urlencode({"key": api_key, "steamids": steam_id})
    request = Request(f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0001/?{params}", headers=DISCORD_HEADERS)
    with urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    players = payload.get("response", {}).get("players", [])
    return players[0] if players else {}


def fetch_steam_reforger_minutes(steam_id):
    api_key = os.environ.get("STEAM_WEB_API_KEY", "")
    if not api_key:
        raise RuntimeError("STEAM_WEB_API_KEY is not configured.")
    params = urlencode(
        {
            "key": api_key,
            "steamid": steam_id,
            "format": "json",
            "include_played_free_games": 1,
            "appids_filter[0]": ARMA_REFORGER_STEAM_APP_ID,
        }
    )
    request = Request(f"{STEAM_OWNED_GAMES_URL}?{params}", headers=DISCORD_HEADERS)
    with urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    games = payload.get("response", {}).get("games", [])
    reforger = next((game for game in games if game.get("appid") == ARMA_REFORGER_STEAM_APP_ID), None)
    if not reforger:
        return 0
    return int(reforger.get("playtime_forever", 0))


def extract_playtime_minutes(payload):
    containers = [payload]
    for key in ("data", "stats", "title", "game", "result"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            containers.append(nested)
    for container in containers:
        for key in ("playtime_minutes", "playTimeMinutes", "minutes", "total_minutes"):
            value = container.get(key)
            if value is None:
                continue
            if isinstance(value, str) and value.strip().replace(".", "", 1).isdigit():
                return int(float(value))
            if isinstance(value, (int, float)):
                return int(value)
    raise RuntimeError("Xbox playtime response did not include a usable playtime_minutes field.")


def fetch_xbox_reforger_minutes(gamertag, xuid="", access_token=""):
    if not XBOX_REFORGER_PLAYTIME_URL:
        raise RuntimeError("XBOX_REFORGER_PLAYTIME_URL is not configured.")
    params = {"gamertag": gamertag}
    if xuid:
        params["xuid"] = xuid
    if XBOX_REFORGER_TITLE_ID:
        params["title_id"] = XBOX_REFORGER_TITLE_ID
    headers = dict(DISCORD_HEADERS)
    if XBOX_API_KEY:
        headers["X-API-Key"] = XBOX_API_KEY
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    xbox_request = Request(f"{XBOX_REFORGER_PLAYTIME_URL}?{urlencode(params)}", headers=headers)
    with urlopen(xbox_request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return extract_playtime_minutes(payload)


def sync_steam_gameplay_points(user_id):
    users = load_users()
    updated_user = None
    awarded = 0
    for saved in users:
        if saved["id"] != user_id:
            continue
        if not saved.get("steam_id"):
            raise RuntimeError("Link Steam before syncing Arma Reforger gameplay time.")
        playtime_minutes = fetch_steam_reforger_minutes(saved["steam_id"])
        credited_minutes = int(saved.get("steam_minutes_credited", 0) or 0)
        new_minutes = max(0, playtime_minutes - credited_minutes)
        awarded = millipoints((new_minutes / 60) * GAMEPLAY_POINT_RATE)
        saved["steam_playtime_minutes"] = playtime_minutes
        saved["steam_minutes_credited"] = max(credited_minutes, playtime_minutes)
        saved["steam_last_sync"] = datetime.now(timezone.utc).isoformat()
        if awarded > 0:
            saved["account_points"] = millipoints(saved.get("account_points", 0) + awarded)
            credit_id = f"steam_{secrets.token_hex(5)}"
            saved.setdefault("supported_server_sessions", []).append(
                {
                    "id": credit_id,
                    "server_name": "Steam Arma Reforger gameplay",
                    "hours": millipoints(new_minutes / 60),
                    "points": awarded,
                    "note": "Steam verified total Arma Reforger playtime delta",
                    "source": "steam",
                    "recorded_at": saved["steam_last_sync"],
                    "status": "Verified",
                }
            )
            saved.setdefault("point_transactions", []).insert(
                0,
                {
                    "id": f"credit_{credit_id}",
                    "type": "credit",
                    "source": "steam",
                    "label": "Arma Reforger gameplay",
                    "points": awarded,
                    "hours": millipoints(new_minutes / 60),
                    "reference": "",
                    "note": "Steam playtime synced into account points.",
                    "created_at": saved["steam_last_sync"],
                    "balance_after": saved["account_points"],
                },
            )
        updated_user = saved
        break
    if updated_user:
        save_users(users)
        if session.get("account", {}).get("id") == updated_user["id"]:
            session["account"] = public_user(updated_user)
    return updated_user, awarded


def sync_xbox_gameplay_points(user_id):
    users = load_users()
    updated_user = None
    awarded = 0
    for saved in users:
        if saved["id"] != user_id:
            continue
        if not saved.get("xbox_gamertag") and not saved.get("xbox_xuid"):
            raise RuntimeError("Link an Xbox account before syncing Arma Reforger gameplay time.")
        playtime_minutes = fetch_xbox_reforger_minutes(
            saved.get("xbox_gamertag", ""),
            saved.get("xbox_xuid", ""),
            saved.get("xbox_access_token", ""),
        )
        credited_minutes = int(saved.get("xbox_minutes_credited", 0) or 0)
        new_minutes = max(0, playtime_minutes - credited_minutes)
        awarded = millipoints((new_minutes / 60) * GAMEPLAY_POINT_RATE)
        saved["xbox_playtime_minutes"] = playtime_minutes
        saved["xbox_minutes_credited"] = max(credited_minutes, playtime_minutes)
        saved["xbox_last_sync"] = datetime.now(timezone.utc).isoformat()
        if awarded > 0:
            saved["account_points"] = millipoints(saved.get("account_points", 0) + awarded)
            credit_id = f"xbox_{secrets.token_hex(5)}"
            saved.setdefault("supported_server_sessions", []).append(
                {
                    "id": credit_id,
                    "server_name": "Xbox Arma Reforger gameplay",
                    "hours": millipoints(new_minutes / 60),
                    "points": awarded,
                    "note": "Xbox verified total Arma Reforger playtime delta",
                    "source": "xbox",
                    "recorded_at": saved["xbox_last_sync"],
                    "status": "Verified",
                }
            )
            saved.setdefault("point_transactions", []).insert(
                0,
                {
                    "id": f"credit_{credit_id}",
                    "type": "credit",
                    "source": "xbox",
                    "label": "Arma Reforger gameplay",
                    "points": awarded,
                    "hours": millipoints(new_minutes / 60),
                    "reference": "",
                    "note": "Xbox playtime synced into account points.",
                    "created_at": saved["xbox_last_sync"],
                    "balance_after": saved["account_points"],
                },
            )
        updated_user = saved
        break
    if updated_user:
        save_users(users)
        if session.get("account", {}).get("id") == updated_user["id"]:
            session["account"] = public_user(updated_user)
    return updated_user, awarded


def steam_sync_is_stale(user, minutes=30):
    if not user.get("steam_id"):
        return False
    last_sync = parse_iso(user.get("steam_last_sync"))
    if not last_sync:
        return True
    return (datetime.now(timezone.utc) - last_sync).total_seconds() >= minutes * 60


def xbox_sync_is_stale(user, minutes=30):
    if not user.get("xbox_gamertag") and not user.get("xbox_xuid"):
        return False
    last_sync = parse_iso(user.get("xbox_last_sync"))
    if not last_sync:
        return True
    return (datetime.now(timezone.utc) - last_sync).total_seconds() >= minutes * 60


def normalize_record(record):
    record.setdefault("priority", "Normal")
    record.setdefault("project_type", "Client mod")
    record.setdefault("assignee", "Unassigned")
    record.setdefault("budget_state", "Not quoted")
    record.setdefault("studio_notes", "")
    record.setdefault("client_visible_notes", record.get("notes", "Request received."))
    record.setdefault("last_updated", record.get("created_at", datetime.now(timezone.utc).isoformat()))
    record.setdefault("milestones", [])
    record.setdefault("assets_needed", [])
    record.setdefault("status_index", 0)
    record.setdefault("eta_days", estimate_days_from_score(record.get("score", 0)))
    record.setdefault("timeline_summary", [])
    record.setdefault("pool_status", "standard")
    record.setdefault("auto_review_until", None)
    record.setdefault("claimed_by", "")
    record.setdefault("claimed_by_id", "")
    record.setdefault("client_addons", [])
    record.setdefault("task_checklist", generate_task_checklist(record))
    record.setdefault("hours_estimate", estimate_hours(record.get("score", 0)))
    record.setdefault("advised_donation", advised_donation(record.get("score", 0)))
    record.setdefault("time_entries", [])
    return record


def procedure_for_item(label, reason, item_type):
    reason_text = reason or "Use the selected request details as the acceptance target."
    return [
        {
            "title": f"Review {label}",
            "detail": f"Read the client reason and confirm the desired outcome. Reason: {reason_text}",
            "client_visible": True,
        },
        {
            "title": f"Plan {label}",
            "detail": f"Map required Workbench resources, dependencies, scripts, prefabs, and QA checks for {item_type}.",
            "client_visible": True,
        },
        {
            "title": f"Build {label}",
            "detail": "Complete the implementation in Enfusion Workbench and record production notes.",
            "client_visible": True,
        },
        {
            "title": f"Test {label}",
            "detail": "Run in-editor and multiplayer/client validation, then mark ready for review.",
            "client_visible": True,
        },
    ]


def generate_task_checklist(record):
    tasks = []
    selected_items = []
    for option in record.get("selected_build_options", []):
        selected_items.append(
            {
                "label": option.get("label", "Selected system"),
                "reason": option.get("reason", ""),
                "type": option.get("group", "System"),
            }
        )
    for dependency in record.get("selected_dependencies", []):
        selected_items.append(
            {
                "label": dependency.get("label", "Workshop dependency"),
                "reason": dependency.get("reason", ""),
                "type": "Dependency",
            }
        )
    for module in record.get("selected_modules", []):
        selected_items.append(
            {
                "label": module.get("title", "Selected module"),
                "reason": module.get("description", ""),
                "type": "Legacy module",
            }
        )

    for item_index, item in enumerate(selected_items, start=1):
        for step_index, step in enumerate(procedure_for_item(item["label"], item["reason"], item["type"]), start=1):
            tasks.append(
                {
                    "id": f"task_{item_index}_{step_index}",
                    "item": item["label"],
                    "title": step["title"],
                    "detail": step["detail"],
                    "client_visible": step["client_visible"],
                    "done": False,
                    "done_by": "",
                    "done_at": "",
                }
            )

    if not tasks:
        tasks.append(
            {
                "id": "task_1_1",
                "item": "Request review",
                "title": "Review request",
                "detail": "Confirm scope and prepare an initial studio plan.",
                "client_visible": True,
                "done": False,
                "done_by": "",
                "done_at": "",
            }
        )
    return tasks


def task_progress(record):
    tasks = [task for task in record.get("task_checklist", []) if task.get("client_visible", True)]
    done = [task for task in tasks if task.get("done")]
    percent = round((len(done) / len(tasks)) * 100) if tasks else 0
    return {"total": len(tasks), "done": len(done), "percent": percent}


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def estimate_days_from_score(score):
    return max(1, min(120, round(score / 18)))


def timeline_days(points, reason_points=0, kind="system"):
    divisor = 12 if kind == "system" else 16
    return max(1, round((points + reason_points) / divisor))


def millipoints(value):
    return round(float(value), 3)


def reason_detail_score(reason, kind="system"):
    words = [word for word in reason.replace("\n", " ").split(" ") if word.strip()]
    unique_words = len({word.lower().strip(".,:;!?()[]") for word in words if word.strip(".,:;!?()[]")})
    sentence_count = max(1, reason.count(".") + reason.count("?") + reason.count("!") + reason.count("\n"))
    if kind == "dependency":
        cap = 18
        score = len(words) * 0.118 + unique_words * 0.037 + sentence_count * 0.071
    else:
        cap = 28
        score = len(words) * 0.173 + unique_words * 0.041 + sentence_count * 0.119
    return millipoints(min(cap, score))


def estimate_hours(score):
    return millipoints(max(0.25, score / POINTS_PER_HOUR))


def point_cash_value(points):
    return millipoints(points * POINT_CASH_RATE)


def advised_donation(score):
    return millipoints(score * POINT_DONATION_RATE)


def total_tracked_hours(record):
    total_seconds = 0
    now = datetime.now(timezone.utc)
    for entry in record.get("time_entries", []):
        start = parse_iso(entry.get("start"))
        end = parse_iso(entry.get("end")) or now
        if start and end > start:
            total_seconds += (end - start).total_seconds()
    return millipoints(total_seconds / 3600)


def total_entry_hours(entries):
    total_seconds = 0
    now = datetime.now(timezone.utc)
    for entry in entries or []:
        start = parse_iso(entry.get("start"))
        end = parse_iso(entry.get("end")) or now
        if start and end > start:
            total_seconds += (end - start).total_seconds()
    return millipoints(total_seconds / 3600)


def staff_time_stats(records, user):
    user_id = user.get("id")
    username = user.get("username", "")
    assigned_records = [
        record
        for record in records
        if record.get("assignee", "").lower() == username.lower()
        or record.get("claimed_by_id") == user_id
    ]
    project_entries = []
    active_project_timers = []
    for record in records:
        for entry in record.get("time_entries", []):
            if entry.get("user_id") != user_id:
                continue
            enriched = {**entry, "reference": record.get("reference"), "project_name": record.get("project_name")}
            project_entries.append(enriched)
            if not entry.get("end"):
                active_project_timers.append(enriched)

    studio_entries = user.get("studio_time_entries", [])
    active_studio_timer = next((entry for entry in reversed(studio_entries) if not entry.get("end")), None)
    completed_tasks = 0
    visible_tasks = 0
    for record in records:
        for task in record.get("task_checklist", []):
            if task.get("done_by") == username:
                completed_tasks += 1
            if task.get("client_visible", True):
                visible_tasks += 1

    role = user.get("role", "developer")
    studio_name = user.get("studio_name") or "Thunder Buddies Studios"
    is_tbs = "thunder" in studio_name.lower() and "budd" in studio_name.lower()
    return {
        "role_dashboard": ROLE_DASHBOARDS.get(role, ROLE_DASHBOARDS["developer"]),
        "studio_name": studio_name,
        "network_label": "Thunder Buddies Developer" if is_tbs else "Third-party Developer" if role == "developer" else "General Staff" if role == "staff" else f"{role.title()} Staff",
        "is_thunder_buddies": is_tbs,
        "assigned_count": len(assigned_records),
        "assigned_records": assigned_records,
        "project_hours": total_entry_hours(project_entries),
        "studio_hours": total_entry_hours(studio_entries),
        "active_project_timers": active_project_timers,
        "active_studio_timer": active_studio_timer,
        "completed_tasks": completed_tasks,
        "visible_tasks": visible_tasks,
        "project_entries": sorted(project_entries, key=lambda entry: entry.get("start", ""), reverse=True)[:8],
        "studio_entries": sorted(studio_entries, key=lambda entry: entry.get("start", ""), reverse=True)[:8],
    }


def refresh_freelance_pool(records):
    now = datetime.now(timezone.utc)
    changed = False
    for record in records:
        if record.get("pool_status") != "auto_review":
            continue
        release_at = parse_iso(record.get("auto_review_until"))
        if release_at and now >= release_at:
            record["pool_status"] = "freelance_pool"
            record["priority"] = "Backlog"
            record["client_visible_notes"] = (
                "This request is above the 30-day Thunder Buddies production lane. "
                "Auto review is complete and the ticket is now available in the freelance pool."
            )
            record["notes"] = record["client_visible_notes"]
            record["last_updated"] = now.isoformat()
            changed = True
    return changed


def read_http_error(exc):
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    if body:
        return f"HTTP {exc.code}: {body[:500]}"
    return f"HTTP {exc.code}: {exc.reason}"


def make_reference(existing):
    used = {item["reference"] for item in existing}
    while True:
        reference = f"TBS-RF-{secrets.randbelow(9000) + 1000}"
        if reference not in used:
            return reference


def complexity_tier(score):
    if score >= 170:
        return "Campaign grade"
    if score >= 120:
        return "Heavy build"
    if score >= 75:
        return "Advanced"
    if score >= 35:
        return "Standard"
    return "Recon"


def phase_slug(index):
    if index < 0 or index >= len(PHASES):
        return "Unknown"
    return PHASES[index]


def sort_records(records):
    priority_weight = {"Critical": 4, "High": 3, "Normal": 2, "Backlog": 1}
    return sorted(
        records,
        key=lambda item: (
            item.get("status_index", 0) >= len(PHASES) - 1,
            -priority_weight.get(item.get("priority", "Normal"), 2),
            -item.get("score", 0),
            item.get("created_at", ""),
        ),
    )


def dashboard_metrics(records):
    active = [record for record in records if record.get("status_index", 0) < len(PHASES) - 1]
    freelance_pool = [record for record in records if record.get("pool_status") == "freelance_pool"]
    auto_review = [record for record in records if record.get("pool_status") == "auto_review"]
    total_complexity = sum(record.get("score", 0) for record in active)
    high_risk = [
        record
        for record in active
        if record.get("score", 0) >= 120 or record.get("priority") in {"High", "Critical"}
    ]
    by_phase = []
    for index, phase in enumerate(PHASES):
        phase_records = [record for record in records if record.get("status_index", 0) == index]
        by_phase.append({"name": phase, "count": len(phase_records), "records": phase_records})

    module_counts = {}
    for record in records:
        for module in record.get("selected_modules", []):
            title = module.get("title", "Unknown module")
            module_counts[title] = module_counts.get(title, 0) + 1

    return {
        "total": len(records),
        "active": len(active),
        "completed": len(records) - len(active),
        "high_risk": len(high_risk),
        "freelance_pool": len(freelance_pool),
        "auto_review": len(auto_review),
        "avg_complexity": round(total_complexity / len(active)) if active else 0,
        "by_phase": by_phase,
        "module_counts": sorted(module_counts.items(), key=lambda item: item[1], reverse=True),
    }


def economy_metrics(records, users=None):
    users = users or []
    active = [record for record in records if record.get("status_index", 0) < len(PHASES) - 1]
    completed = [record for record in records if record.get("status_index", 0) >= len(PHASES) - 1]
    pooled = [record for record in records if record.get("pool_status") in {"auto_review", "freelance_pool", "claimed_freelance"}]
    total_points = sum(record.get("score", 0) for record in records)
    active_points = sum(record.get("score", 0) for record in active)
    pool_points = sum(record.get("score", 0) for record in pooled)
    completed_points = sum(record.get("score", 0) for record in completed)
    account_points = sum(user.get("account_points", 0) for user in users if user.get("role") == "customer")
    earned_points = sum(
        transaction.get("points", 0)
        for user in users
        for transaction in user.get("point_transactions", [])
        if transaction.get("type") == "credit"
    )
    spent_points = sum(
        transaction.get("points", 0)
        for user in users
        for transaction in user.get("point_transactions", [])
        if transaction.get("type") == "debit"
    )
    production_circulating_points = active_points + pool_points
    circulating_points = millipoints(account_points + production_circulating_points)
    circulation_hours = estimate_hours(circulating_points)
    production_hours = estimate_hours(production_circulating_points)
    bank_hours = estimate_hours(account_points)
    return {
        "total_points": total_points,
        "active_points": active_points,
        "pool_points": pool_points,
        "completed_points": completed_points,
        "account_points": millipoints(account_points),
        "earned_points": millipoints(earned_points),
        "spent_points": millipoints(spent_points),
        "production_circulating_points": millipoints(production_circulating_points),
        "circulating_points": circulating_points,
        "circulation_hours": circulation_hours,
        "production_hours": production_hours,
        "bank_hours": bank_hours,
        "estimated_circulation_value": round(circulation_hours * DEV_HOURLY_RATE),
        "estimated_pipeline_value": round(production_hours * DEV_HOURLY_RATE),
        "estimated_bank_value": round(bank_hours * DEV_HOURLY_RATE),
        "estimated_pool_value": round(estimate_hours(pool_points) * DEV_HOURLY_RATE),
        "estimated_completed_value": round(estimate_hours(completed_points) * DEV_HOURLY_RATE),
        "hourly_rate": DEV_HOURLY_RATE,
        "points_per_hour": POINTS_PER_HOUR,
        "average_eta": round(sum(record.get("eta_days", 0) for record in records) / len(records)) if records else 0,
    }


def role_counts(users):
    counts = {role: 0 for role in ROLES}
    for user in users:
        role = user.get("role", "customer")
        counts[role] = counts.get(role, 0) + 1
    return counts


def charity_admin_queue(users):
    donations = []
    for user in users:
        for donation in user.get("charity_donations", []):
            donations.append(
                {
                    **donation,
                    "username": user.get("username", ""),
                    "email": user.get("email", ""),
                }
            )
    return sorted(donations, key=lambda item: item.get("created_at", ""), reverse=True)


def client_metrics(records):
    active = [record for record in records if record.get("status_index", 0) < len(PHASES) - 1]
    review = [record for record in records if record.get("status_index", 0) == 5]
    return {
        "total": len(records),
        "active": len(active),
        "review": len(review),
        "completed": len(records) - len(active),
    }


def client_portal_context(user, records, active_tab, error=""):
    initial_pages = workshop_initial_pages()
    return {
        "user": user,
        "records": records,
        "metrics": client_metrics(records),
        "phases": PHASES,
        "modules": MODULES,
        "build_option_groups": BUILD_OPTION_GROUPS,
        "workshop_dependencies": workshop_dependencies_for_builder(initial_pages),
        "workshop_next_page": initial_pages + 1,
        "tabs": CLIENT_TABS,
        "active_tab": active_tab,
        "gameplay_point_rate": GAMEPLAY_POINT_RATE,
        "point_cash_rate": point_cash_value(1),
        "featured_charity_causes": sorted({item["cause"] for item in FEATURED_CHARITIES}),
        "has_linked_game_account": user_has_linked_game_account(user),
        "has_linked_xbox_account": bool(user.get("xbox_gamertag") or user.get("xbox_xuid")),
        "linked_reforger_hours": linked_reforger_hours(user),
        "steam_app_id": ARMA_REFORGER_STEAM_APP_ID,
        "featured_charities": FEATURED_CHARITIES,
        "gofundme_search_url": GOFUNDME_CHARITY_SEARCH_URL,
        "notice": session.pop("client_notice", ""),
        "error": error,
    }


def calculate_complexity(form):
    score = 0
    selected = []
    selected_build_options = []
    selected_dependencies = []
    timeline_summary = []

    for module in MODULES:
        enabled = form.get(f"{module['id']}_enabled") == "on"
        description = form.get(f"{module['id']}_description", "").strip()
        if not enabled:
            continue

        word_count = len(description.split())
        detail_points = min(18, word_count // 8)
        module_score = module["base"] + module["risk"] + detail_points

        score += module_score
        selected.append(
            {
                "id": module["id"],
                "title": module["title"],
                "description": description,
                "points": module_score,
            }
        )

    for group in BUILD_OPTION_GROUPS:
        for option in group["options"]:
            if form.get(f"buildopt_{option['id']}") != "on":
                continue
            reason = form.get(f"buildopt_{option['id']}_reason", "").strip()
            reason_points = reason_detail_score(reason, "system")
            option_score = millipoints(option["points"] + reason_points)
            eta_days = timeline_days(option["points"], reason_points, "system")
            score += option_score
            selected_build_options.append(
                {
                    "group": group["title"],
                    "id": option["id"],
                    "label": option["label"],
                    "points": option_score,
                    "base_points": option["points"],
                    "reason_points": reason_points,
                    "reason": reason,
                    "eta_days": eta_days,
                }
            )
            timeline_summary.append(
                {
                    "label": option["label"],
                    "type": group["title"],
                    "eta_days": eta_days,
                    "points": option_score,
                }
            )

    dependency_ids = sorted(
        {
            key[4:]
            for key in form.keys()
            if key.startswith("dep_")
            and not key.endswith("_reason")
            and not key.endswith("_label")
            and not key.endswith("_author")
            and not key.endswith("_points")
            and not key.endswith("_workshop_id")
            and not key.endswith("_source_url")
        }
    )
    fallback_by_id = {dependency["id"]: dependency for dependency in WORKSHOP_FALLBACK_DEPENDENCIES}
    for dependency_id in dependency_ids:
        if form.get(f"dep_{dependency_id}") != "on":
            continue
        fallback_dependency = fallback_by_id.get(dependency_id, {})
        label = form.get(f"dep_{dependency_id}_label", fallback_dependency.get("label", "Workshop dependency")).strip()
        author = form.get(f"dep_{dependency_id}_author", fallback_dependency.get("author", "Workshop")).strip()
        workshop_id = form.get(f"dep_{dependency_id}_workshop_id", fallback_dependency.get("workshop_id", "")).strip()
        source_url = form.get(f"dep_{dependency_id}_source_url", fallback_dependency.get("source_url", "")).strip()
        try:
            base_points = float(form.get(f"dep_{dependency_id}_points", fallback_dependency.get("points", 8)))
        except (TypeError, ValueError):
            base_points = 8
        reason = form.get(f"dep_{dependency_id}_reason", "").strip()
        reason_points = reason_detail_score(reason, "dependency")
        dependency_score = millipoints(base_points + reason_points)
        eta_days = timeline_days(base_points, reason_points, "dependency")
        score += dependency_score
        selected_dependencies.append(
            {
                "id": dependency_id,
                "workshop_id": workshop_id,
                "label": label,
                "author": author,
                "source_url": source_url,
                "points": dependency_score,
                "base_points": base_points,
                "reason_points": reason_points,
                "reason": reason,
                "eta_days": eta_days,
            }
        )
        timeline_summary.append(
            {
                "label": label,
                "type": "Workshop dependency",
                "eta_days": eta_days,
                "points": dependency_score,
            }
        )

    custom_description = form.get("custom_description", "").strip()
    if form.get("custom_enabled") == "on" and custom_description:
        detail_points = max(8, reason_detail_score(custom_description, "system"))
        eta_days = timeline_days(detail_points, 0, "system")
        score += detail_points
        selected_build_options.append(
            {
                "group": "Custom",
                "id": "custom_notes",
                "label": "Custom request notes",
                "points": detail_points,
                "base_points": detail_points,
                "reason_points": 0,
                "reason": custom_description,
                "eta_days": eta_days,
            }
        )
        timeline_summary.append(
            {
                "label": "Custom request notes",
                "type": "Custom",
                "eta_days": eta_days,
                "points": detail_points,
            }
        )

    deadline = form.get("deadline", "standard")
    deadline_points = {"standard": 0, "soon": 12, "rush": 28}.get(deadline, 0)
    score += deadline_points

    if len(selected) + len(selected_build_options) >= 4:
        score += 16
    if len(selected) + len(selected_build_options) >= 6:
        score += 24
    if len(selected_dependencies) >= 3:
        score += 12
    if len(selected_dependencies) >= 6:
        score += 18
    score = millipoints(score)

    eta_days = max(1, sum(item["eta_days"] for item in timeline_summary))
    if deadline == "soon":
        eta_days += 2
    if deadline == "rush":
        eta_days += 4

    return {
        "score": score,
        "tier": complexity_tier(score),
        "selected_modules": selected,
        "selected_build_options": selected_build_options,
        "selected_dependencies": selected_dependencies,
        "timeline_summary": timeline_summary,
        "eta_days": eta_days,
        "hours_estimate": estimate_hours(score),
        "advised_donation": advised_donation(score),
        "deadline_points": deadline_points,
    }


def current_user():
    account = session.get("account")
    if account:
        for saved in load_users():
            if saved.get("id") == account.get("id"):
                session["account"] = public_user(saved)
                return session["account"]
        return account
    return {
        "id": "guest",
        "username": "Guest builder",
        "email": "",
        "role": "guest",
        "avatar": None,
        "prototype": True,
    }


def login_user(user):
    users = load_users()
    for saved in users:
        if saved["id"] == user["id"]:
            saved["last_login"] = datetime.now(timezone.utc).isoformat()
            user = saved
            break
    save_users(users)
    session["account"] = public_user(user)


def studio_unlocked():
    return current_user().get("role") in STAFF_ROLES


def admin_unlocked():
    return current_user().get("role") == "admin"


def admin_permissions_unlocked():
    return admin_unlocked() and session.get("admin_permissions_unlocked") is True


def studio_tabs_for_user(user):
    role = user.get("role")
    studio_name = user.get("studio_name") or ""
    is_tbs_developer = role == "developer" and "thunder" in studio_name.lower() and "budd" in studio_name.lower()
    if role == "admin":
        return STUDIO_TABS
    if is_tbs_developer:
        return ["Command", "Projects", "Pipeline", "Complexity", "Freelance Pool", "Settings"]
    if role == "developer":
        return ["Command", "Projects", "Freelance Pool", "Settings"]
    if role == "moderator":
        return ["Command", "Clients", "Pipeline", "Freelance Pool", "Settings"]
    if role == "tester":
        return ["Command", "Projects", "Pipeline", "Complexity", "Settings"]
    if role == "staff":
        return ["Command", "Clients", "Settings"]
    return ["Command", "Settings"]


def records_for_user(records, user):
    if user.get("role") == "admin":
        return records
    return [
        record
        for record in records
        if record.get("discord_id") == user["id"]
        or record.get("discord_name", "").lower() == user["username"].lower()
        or record.get("client_user_id") == user["id"]
    ]


@app.before_request
def protect_studio_routes():
    if not request.path.startswith("/studio"):
        return None
    if request.endpoint in {"static"}:
        return None
    if studio_unlocked():
        return None
    return redirect(url_for("login", next=request.path))


@app.before_request
def protect_suspended_clients():
    account = current_user()
    if account.get("role") != "customer" or not account.get("suspended"):
        return None
    allowed = {"logout", "home", "legal", "static"}
    if request.endpoint in allowed:
        return None
    if request.path.startswith("/static"):
        return None
    return render_template("login.html", mode="login", error=f"Account suspended: {account.get('suspension_reason') or 'Contact Thunder Buddies Studios.'}", next_url=""), 403


@app.get("/")
def home():
    records = load_requests()
    user = current_user()
    user_records = [item for item in records if item.get("discord_id") == user["id"]]
    return render_template(
        "index.html",
        modules=MODULES,
        phases=PHASES,
        user=user,
        request_count=len(user_records),
        latest_reference=user_records[-1]["reference"] if user_records else None,
    )


@app.get("/legal")
def legal():
    return render_template("legal.html")


@app.get("/login")
def login():
    if current_user().get("role") in ROLES:
        return redirect(url_for("dashboard"))
    return render_template("login.html", mode=request.args.get("mode", "login"), next_url=request.args.get("next", ""))


@app.post("/login")
def login_post():
    identifier = request.form.get("identifier", "")
    password = request.form.get("password", "")
    user = find_user(identifier)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html",
            mode="login",
            error="That email, username, or password did not match.",
            next_url=request.form.get("next", ""),
        ), 401

    login_user(user)
    next_url = request.form.get("next") or ""
    if next_url.startswith("/studio") and current_user().get("role") in {"developer", "admin"}:
        return redirect(next_url)
    return redirect(url_for("dashboard"))


@app.post("/register")
def register_post():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "customer")
    access_code = request.form.get("access_code", "")

    if role not in ROLES:
        role = "customer"
    if not username or not email or not password:
        return render_template("login.html", mode="register", error="Username, email, and password are required.", next_url=""), 400
    if find_user(email) or find_user(username):
        return render_template("login.html", mode="register", error="That account already exists.", next_url=""), 409
    if not access_code_allows(role, access_code):
        return render_template("login.html", mode="register", error="That role access code is not valid.", next_url=""), 403

    user = create_user(username, email, password, role)
    login_user(user)
    return redirect(url_for("dashboard"))


@app.get("/dashboard")
def dashboard():
    role = current_user().get("role")
    if role == "admin":
        return redirect(url_for("studio_dashboard", tab="Command"))
    if role in STAFF_ROLES:
        return redirect(url_for("studio_dashboard"))
    if role == "customer":
        return redirect(url_for("client_portal"))
    return redirect(url_for("login"))


@app.get("/client")
def client_portal():
    user = current_user()
    if user.get("role") not in {"customer", "admin"}:
        return redirect(url_for("login", next=request.path))
    records = sort_records(records_for_user(load_requests(), user))
    active_tab = request.args.get("tab", "Overview")
    if active_tab not in CLIENT_TABS:
        active_tab = "Overview"
    if active_tab in {"Overview", "Account", "New Build"}:
        awarded_total = 0
        if steam_sync_is_stale(user):
            try:
                synced_user, awarded = sync_steam_gameplay_points(user["id"])
                if synced_user:
                    user = public_user(synced_user)
                awarded_total += awarded
            except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, KeyError):
                pass
        if xbox_sync_is_stale(user):
            try:
                synced_user, awarded = sync_xbox_gameplay_points(user["id"])
                if synced_user:
                    user = public_user(synced_user)
                awarded_total += awarded
            except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, KeyError):
                pass
        if awarded_total > 0:
            session["client_notice"] = f"Gameplay sync added {awarded_total} points from new Arma Reforger playtime."

    return render_template("client.html", **client_portal_context(user, records, active_tab))


@app.post("/client/account")
def update_client_account():
    user = current_user()
    if user.get("role") not in {"customer", "admin"}:
        return redirect(url_for("login", next="/client"))

    users = load_users()
    for saved in users:
        if saved["id"] == user["id"]:
            saved["reforger_player_id"] = request.form.get("reforger_player_id", "").strip()
            session["account"] = public_user(saved)
            break
    save_users(users)
    return redirect(url_for("client_portal", tab="Account"))


@app.get("/steam/link")
def steam_link():
    user = current_user()
    if user.get("role") not in {"customer", "admin"}:
        return redirect(url_for("login", next="/client?tab=Account"))

    state = secrets.token_urlsafe(20)
    session["steam_openid_state"] = state
    return_to = url_for("steam_callback", _external=True, state=state)
    params = urlencode(
        {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.mode": "checkid_setup",
            "openid.return_to": return_to,
            "openid.realm": request.url_root.rstrip("/"),
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        }
    )
    return redirect(f"{STEAM_OPENID_URL}?{params}")


@app.get("/steam/callback")
def steam_callback():
    user = current_user()
    if user.get("role") not in {"customer", "admin"}:
        return redirect(url_for("login", next="/client?tab=Account"))
    if request.args.get("state") != session.pop("steam_openid_state", None):
        session["client_notice"] = "Steam link failed because the login state did not match."
        return redirect(url_for("client_portal", tab="Account"))

    verification = dict(request.args)
    verification["openid.mode"] = "check_authentication"
    try:
        verify_request = Request(
            STEAM_OPENID_URL,
            data=urlencode(verification).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded", **DISCORD_HEADERS},
        )
        with urlopen(verify_request, timeout=8) as response:
            result = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError):
        session["client_notice"] = "Steam could not verify the account link. Try again in a moment."
        return redirect(url_for("client_portal", tab="Account"))

    if "is_valid:true" not in result:
        session["client_notice"] = "Steam rejected the account verification."
        return redirect(url_for("client_portal", tab="Account"))

    claimed_id = request.args.get("openid.claimed_id", "")
    match = re.search(r"/openid/id/(\d+)$", claimed_id)
    if not match:
        session["client_notice"] = "Steam did not return a usable SteamID64."
        return redirect(url_for("client_portal", tab="Account"))

    steam_id = match.group(1)
    profile = {}
    try:
        profile = fetch_steam_profile(steam_id)
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, KeyError):
        profile = {}

    users = load_users()
    for saved in users:
        if saved["id"] == user["id"]:
            saved["steam_id"] = steam_id
            saved["steam_name"] = profile.get("personaname", "")
            saved["steam_avatar"] = profile.get("avatarfull", "")
            session["account"] = public_user(saved)
            break
    save_users(users)

    try:
        updated_user, awarded = sync_steam_gameplay_points(user["id"])
        hours = millipoints((updated_user.get("steam_playtime_minutes", 0) or 0) / 60)
        session["client_notice"] = f"Steam linked. Arma Reforger playtime: {hours} hours. Awarded {awarded} points."
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, KeyError) as exc:
        session["client_notice"] = f"Steam linked, but playtime sync needs attention: {exc}"
    return redirect(url_for("client_portal", tab="Account"))


@app.post("/steam/sync")
def steam_sync():
    user = current_user()
    if user.get("role") not in {"customer", "admin"}:
        return redirect(url_for("login", next="/client?tab=Account"))
    try:
        updated_user, awarded = sync_steam_gameplay_points(user["id"])
        hours = millipoints((updated_user.get("steam_playtime_minutes", 0) or 0) / 60)
        session["client_notice"] = f"Steam synced. Arma Reforger playtime: {hours} hours. Awarded {awarded} new points."
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, KeyError) as exc:
        session["client_notice"] = f"Steam sync failed: {exc}"
    return redirect(url_for("client_portal", tab="Account"))


@app.get("/login/xbox")
def xbox_login():
    return render_template(
        "login.html",
        mode="login",
        error="Xbox OAuth login is disabled for now. Create or log into a website account, then link your Xbox gamertag/XUID from the Account tab.",
        next_url="",
    ), 400


@app.post("/xbox/link")
def xbox_link():
    user = current_user()
    if user.get("role") not in {"customer", "admin"}:
        return redirect(url_for("login", next="/client?tab=Account"))
    gamertag = request.form.get("xbox_gamertag", "").strip()
    xuid = request.form.get("xbox_xuid", "").strip()
    if not gamertag and not xuid:
        session["client_notice"] = "Enter an Xbox gamertag or XUID to link the account."
        return redirect(url_for("client_portal", tab="Account"))

    existing_link = find_user_by_xbox_identity(xuid, gamertag)
    if existing_link and existing_link.get("id") != user.get("id"):
        session["client_notice"] = "That Xbox account is already linked to another customer account."
        return redirect(url_for("client_portal", tab="Account"))

    users = load_users()
    for saved in users:
        if saved["id"] == user["id"]:
            saved["xbox_gamertag"] = gamertag or saved.get("xbox_gamertag", "")
            saved["xbox_xuid"] = xuid or saved.get("xbox_xuid", "")
            saved["xbox_access_token"] = ""
            saved["xbox_refresh_token"] = ""
            saved["xbox_token_expires_at"] = ""
            session["account"] = public_user(saved)
            break
    save_users(users)
    session["client_notice"] = "Xbox account linked. Playtime sync requires the configured Xbox playtime API, or you can submit proof for review."
    return redirect(url_for("client_portal", tab="Account"))


@app.post("/xbox/playtime-proof")
def xbox_playtime_proof():
    user = current_user()
    if user.get("role") not in {"customer", "admin"}:
        return redirect(url_for("login", next="/client?tab=Account"))
    if not (user.get("xbox_gamertag") or user.get("xbox_xuid")):
        session["client_notice"] = "Link your Xbox account before submitting Xbox playtime proof."
        return redirect(url_for("client_portal", tab="Account"))

    try:
        hours_claimed = millipoints(request.form.get("hours_claimed", 0))
    except ValueError:
        hours_claimed = 0
    if hours_claimed <= 0:
        session["client_notice"] = "Enter the Xbox hours shown in your screenshot before submitting."
        return redirect(url_for("client_portal", tab="Account"))
    if request.form.get("confirm_visibility") != "on":
        session["client_notice"] = "Confirm that the screenshot clearly shows your gamertag and hours."
        return redirect(url_for("client_portal", tab="Account"))

    proof_image = request.files.get("proof_image")
    if not proof_image or not proof_image.filename:
        session["client_notice"] = "Upload a screenshot that clearly shows your gamertag and hours."
        return redirect(url_for("client_portal", tab="Account"))

    filename = safe_upload_filename(user.get("id", "xbox"), proof_image.filename)
    ensure_storage()
    target_path = XBOX_PROOF_UPLOAD_DIR / filename
    proof_image.save(target_path)
    image_url = url_for("static", filename=f"uploads/xbox-proofs/{filename}")

    users = load_users()
    for saved in users:
        if saved["id"] != user["id"]:
            continue
        saved.setdefault("xbox_playtime_submissions", []).insert(
            0,
            {
                "id": f"xproof_{secrets.token_hex(5)}",
                "gamertag": saved.get("xbox_gamertag", "") or saved.get("xbox_xuid", "Xbox user"),
                "hours_claimed": hours_claimed,
                "image_url": image_url,
                "note": request.form.get("note", "").strip(),
                "status": "Pending manual review",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        session["account"] = public_user(saved)
        break
    save_users(users)
    session["client_notice"] = "Xbox play hours submitted for review. Make sure the screenshot clearly shows your gamertag and hours."
    return redirect(url_for("client_portal", tab="Account"))


@app.post("/studio/freelance/claim/<reference>")
def claim_freelance(reference):
    account = current_user()
    records = load_requests()
    record = next((item for item in records if item["reference"].upper() == reference.upper()), None)
    if not record:
        return render_template("not_found.html", reference=reference), 404
    if record.get("pool_status") != "freelance_pool":
        return redirect(url_for("studio_dashboard", tab="Freelance Pool"))

    record["pool_status"] = "claimed_freelance"
    record["claimed_by"] = account["username"]
    record["claimed_by_id"] = account["id"]
    record["assignee"] = account["username"]
    record["priority"] = "Normal"
    record["status_index"] = 2
    record["client_visible_notes"] = (
        f"This request has been claimed from the freelance pool by {account['username']} "
        "for estimate review. Thunder Buddies direct production is still not started."
    )
    record["notes"] = record["client_visible_notes"]
    record["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_requests(records)
    return redirect(url_for("studio_dashboard", tab="Freelance Pool"))


@app.post("/studio/timer/start")
def start_studio_timer():
    account = current_user()
    if account.get("role") not in STAFF_ROLES:
        return redirect(url_for("login", next="/studio"))

    users = load_users()
    for user in users:
        if user["id"] != account["id"]:
            continue
        running = [entry for entry in user.setdefault("studio_time_entries", []) if not entry.get("end")]
        if not running:
            user["studio_time_entries"].append(
                {
                    "id": f"studio_time_{secrets.token_hex(5)}",
                    "start": datetime.now(timezone.utc).isoformat(),
                    "end": "",
                    "note": request.form.get("note", "").strip(),
                    "mode": request.form.get("mode", "Studio operations").strip() or "Studio operations",
                }
            )
            session["account"] = public_user(user)
        break
    save_users(users)
    return redirect(url_for("studio_dashboard", tab=request.form.get("return_tab", "Command")))


@app.post("/studio/timer/stop")
def stop_studio_timer():
    account = current_user()
    if account.get("role") not in STAFF_ROLES:
        return redirect(url_for("login", next="/studio"))

    users = load_users()
    for user in users:
        if user["id"] != account["id"]:
            continue
        for entry in reversed(user.setdefault("studio_time_entries", [])):
            if not entry.get("end"):
                entry["end"] = datetime.now(timezone.utc).isoformat()
                break
        session["account"] = public_user(user)
        break
    save_users(users)
    return redirect(url_for("studio_dashboard", tab=request.form.get("return_tab", "Command")))


@app.post("/requests/<reference>/tasks/<task_id>/toggle")
def toggle_request_task(reference, task_id):
    if current_user().get("role") not in STAFF_ROLES:
        return redirect(url_for("login", next=f"/requests/{reference}"))

    records = load_requests()
    record = next((item for item in records if item["reference"].upper() == reference.upper()), None)
    if not record:
        return render_template("not_found.html", reference=reference), 404

    for task in record.get("task_checklist", []):
        if task["id"] != task_id:
            continue
        task["done"] = not task.get("done", False)
        task["done_by"] = current_user()["username"] if task["done"] else ""
        task["done_at"] = datetime.now(timezone.utc).isoformat() if task["done"] else ""
        break

    progress = task_progress(record)
    if progress["percent"] >= 100:
        record["status_index"] = max(record.get("status_index", 0), 5)
        record["client_visible_notes"] = "All generated checklist tasks are marked complete and ready for client review."
        record["notes"] = record["client_visible_notes"]
    elif progress["percent"] > 0:
        record["status_index"] = max(record.get("status_index", 0), 3)
        record["client_visible_notes"] = f"Generated task progress is {progress['percent']}% complete."
        record["notes"] = record["client_visible_notes"]

    record["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_requests(records)
    return redirect(url_for("request_detail", reference=reference))


@app.post("/requests/<reference>/addons")
def add_request_addon(reference):
    records = load_requests()
    record = next((item for item in records if item["reference"].upper() == reference.upper()), None)
    if not record:
        return render_template("not_found.html", reference=reference), 404

    addon_text = request.form.get("addon_text", "").strip()
    if addon_text:
        record.setdefault("client_addons", []).append(
            {
                "id": f"addon_{secrets.token_hex(5)}",
                "text": addon_text,
                "created_by": current_user().get("username", "Client"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "Needs studio review",
            }
        )
        record["client_visible_notes"] = "Client added a requested change. Studio review is needed."
        record["notes"] = record["client_visible_notes"]
        record["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_requests(records)

    return redirect(url_for("request_detail", reference=reference))


@app.post("/studio/requests/<reference>/timer/start")
def start_project_timer(reference):
    if current_user().get("role") not in STAFF_ROLES:
        return redirect(url_for("login", next=f"/requests/{reference}"))

    records = load_requests()
    record = next((item for item in records if item["reference"].upper() == reference.upper()), None)
    if not record:
        return render_template("not_found.html", reference=reference), 404

    account = current_user()
    running = [
        entry
        for entry in record.setdefault("time_entries", [])
        if entry.get("user_id") == account["id"] and not entry.get("end")
    ]
    if not running:
        record["time_entries"].append(
            {
                "id": f"time_{secrets.token_hex(5)}",
                "user_id": account["id"],
                "username": account["username"],
                "start": datetime.now(timezone.utc).isoformat(),
                "end": "",
                "note": request.form.get("note", "").strip(),
            }
        )
        record["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_requests(records)
    return redirect(url_for("request_detail", reference=reference))


@app.post("/studio/requests/<reference>/timer/stop")
def stop_project_timer(reference):
    if current_user().get("role") not in STAFF_ROLES:
        return redirect(url_for("login", next=f"/requests/{reference}"))

    records = load_requests()
    record = next((item for item in records if item["reference"].upper() == reference.upper()), None)
    if not record:
        return render_template("not_found.html", reference=reference), 404

    account = current_user()
    for entry in reversed(record.setdefault("time_entries", [])):
        if entry.get("user_id") == account["id"] and not entry.get("end"):
            entry["end"] = datetime.now(timezone.utc).isoformat()
            break
    record["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_requests(records)
    return redirect(url_for("request_detail", reference=reference))


@app.post("/admin/users/<user_id>/role")
def admin_update_user_role(user_id):
    if not admin_permissions_unlocked():
        return redirect(url_for("admin_verify"))

    new_role = request.form.get("role", "customer")
    if new_role not in ROLES:
        new_role = "customer"

    users = load_users()
    for user in users:
        if user["id"] == user_id:
            user["role"] = new_role
            user["suspended"] = request.form.get("suspended") == "on"
            user["suspension_reason"] = request.form.get("suspension_reason", "").strip()
            user["studio_name"] = request.form.get("studio_name", "").strip()
            try:
                user["account_points"] = millipoints(request.form.get("account_points", user.get("account_points", 0)))
            except ValueError:
                user["account_points"] = millipoints(user.get("account_points", 0))
            break
    save_users(users)
    return redirect(url_for("studio_dashboard", tab="Admin"))


@app.get("/admin/verify")
def admin_verify():
    if not admin_unlocked():
        return redirect(url_for("login"))
    return render_template("admin_verify.html")


@app.post("/admin/verify")
def admin_verify_post():
    account = current_user()
    user = find_user(account.get("email", ""))
    password = request.form.get("password", "")
    if user and check_password_hash(user["password_hash"], password):
        session["admin_permissions_unlocked"] = True
        return redirect(url_for("studio_dashboard", tab="Admin"))
    return render_template("admin_verify.html", error="Admin password did not match."), 401


@app.get("/login/discord")
def discord_login():
    client_id = os.environ.get("DISCORD_CLIENT_ID")
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI")
    if client_id and redirect_uri:
        state = secrets.token_urlsafe(24)
        session["discord_oauth_state"] = state
        params = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "identify",
                "state": state,
            }
        )
        return redirect(f"https://discord.com/oauth2/authorize?{params}")

    session["discord_user"] = {
        "id": f"prototype-{secrets.randbelow(999999)}",
        "username": "Discord Prototype User",
        "avatar": None,
        "prototype": True,
    }
    user = create_user(
        username=f"DiscordCustomer{secrets.randbelow(9999)}",
        email=f"discord-{secrets.token_hex(5)}@prototype.local",
        password=secrets.token_urlsafe(16),
        role="customer",
    )
    user["username"] = "Discord Prototype User"
    user["discord_id"] = session["discord_user"]["id"]
    users = load_users()
    for saved in users:
        if saved["id"] == user["id"]:
            saved["username"] = user["username"]
            saved["discord_id"] = user["discord_id"]
    save_users(users)
    login_user(user)
    return redirect(url_for("dashboard"))


@app.get("/auth/discord/callback")
def discord_callback():
    code = request.args.get("code")
    returned_state = request.args.get("state")
    expected_state = session.pop("discord_oauth_state", None)
    client_id = os.environ.get("DISCORD_CLIENT_ID")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET")
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI")

    if request.args.get("error"):
        return render_template(
            "login.html",
            mode="login",
            error=f"Discord rejected the login: {request.args.get('error_description', request.args['error'])}",
            next_url="",
        ), 400

    if not expected_state or not returned_state or not secrets.compare_digest(expected_state, returned_state):
        return render_template(
            "login.html",
            mode="login",
            error="Discord login state did not match. Please try signing in again.",
            next_url="",
        ), 400

    if not code or not client_id or not client_secret or not redirect_uri:
        return render_template(
            "login.html",
            mode="login",
            error="Discord login is missing required server configuration.",
            next_url="",
        ), 500

    token_body = urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    token_request = Request(
        "https://discord.com/api/v10/oauth2/token",
        data=token_body,
        headers={
            **DISCORD_HEADERS,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urlopen(token_request, timeout=10) as response:
            token_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = read_http_error(exc)
        return render_template(
            "login.html",
            mode="login",
            error=f"Discord token exchange failed. Check the Railway redirect URI and Discord client secret. ({detail})",
            next_url="",
        ), 502
    except (URLError, TimeoutError) as exc:
        return render_template(
            "login.html",
            mode="login",
            error=f"Discord token exchange failed. Discord may be unreachable from Railway. ({exc})",
            next_url="",
        ), 502

    access_token = token_payload.get("access_token")
    if not access_token:
        return render_template(
            "login.html",
            mode="login",
            error="Discord did not return an access token. Please try again.",
            next_url="",
        ), 502

    user_request = Request(
        "https://discord.com/api/v10/users/@me",
        headers={
            **DISCORD_HEADERS,
            "Authorization": f"Bearer {access_token}",
        },
    )
    try:
        with urlopen(user_request, timeout=10) as response:
            discord_user = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = read_http_error(exc)
        return render_template(
            "login.html",
            mode="login",
            error=f"Could not fetch your Discord profile. ({detail})",
            next_url="",
        ), 502
    except (URLError, TimeoutError) as exc:
        return render_template(
            "login.html",
            mode="login",
            error=f"Could not fetch your Discord profile. Discord may be unreachable from Railway. ({exc})",
            next_url="",
        ), 502

    discriminator = discord_user.get("discriminator")
    username = discord_user.get("username", "Discord user")
    display_name = username if discriminator in (None, "0") else f"{username}#{discriminator}"

    email = f"discord-{discord_user['id']}@discord.local"
    user = find_user(email)
    if not user:
        user = create_user(display_name, email, secrets.token_urlsafe(24), "customer")
    users = load_users()
    for saved in users:
        if saved["id"] == user["id"]:
            saved["username"] = display_name
            saved["avatar"] = discord_user.get("avatar")
            saved["discord_id"] = discord_user["id"]
            user = saved
            break
    save_users(users)
    login_user(user)
    return redirect(url_for("dashboard"))


@app.post("/requests")
def create_request():
    records = load_requests()
    user = current_user()
    if user.get("role") == "customer" and user.get("suspended"):
        return render_template("login.html", mode="login", error="This client account is suspended and cannot create submissions.", next_url=""), 403
    if user.get("role") == "customer" and not user_has_linked_game_account(user):
        records_for_client = sort_records(records_for_user(records, user))
        return render_template(
            "client.html",
            **client_portal_context(user, records_for_client, "Account", "Link a Steam or Xbox account before creating a submission."),
        ), 403
    complexity = calculate_complexity(request.form)
    available_points = millipoints(user.get("account_points", 0))
    required_points = complexity["score"]
    if user.get("role") == "customer" and available_points < required_points:
        records_for_client = sort_records(records_for_user(records, user))
        message = (
            f"This request needs {required_points} account points. "
            f"You currently have {available_points}. Sync Steam or Xbox Arma Reforger playtime to earn more."
        )
        return render_template("client.html", **client_portal_context(user, records_for_client, "New Build", message)), 402
    reference = make_reference(records)
    now = datetime.now(timezone.utc)
    eta_days = complexity["eta_days"]
    over_internal_lane = eta_days > 30
    client_note = "Request received. Thunder Buddies Studios will review scope and confirm the production lane."
    pool_status = "standard"
    auto_review_until = None
    assignee = "Unassigned"
    priority = "Normal"
    status_index = 0

    if over_internal_lane:
        pool_status = "auto_review"
        auto_review_until = (now.timestamp() + 90)
        auto_review_until = datetime.fromtimestamp(auto_review_until, timezone.utc).isoformat()
        assignee = "Auto review"
        priority = "Backlog"
        status_index = 1
        client_note = (
            "This request currently estimates above 30 days. Thunder Buddies will not proceed directly. "
            "It is in auto review and will release to the freelance pool after 90 seconds if still over lane."
        )

    record = {
        "reference": reference,
        "project_name": request.form.get("project_name", "Untitled Reforger mod").strip(),
        "discord_name": request.form.get("discord_name", user["username"]).strip(),
        "unit_name": request.form.get("unit_name", "").strip(),
        "deadline": request.form.get("deadline", "standard"),
        "discord_id": user["id"],
        "discord_username": user["username"],
        "client_user_id": user["id"],
        "client_email": user.get("email", ""),
        "score": complexity["score"],
        "tier": complexity["tier"],
        "deadline_points": complexity["deadline_points"],
        "selected_modules": complexity["selected_modules"],
        "selected_build_options": complexity["selected_build_options"],
        "selected_dependencies": complexity["selected_dependencies"],
        "timeline_summary": complexity["timeline_summary"],
        "eta_days": eta_days,
        "hours_estimate": complexity["hours_estimate"],
        "advised_donation": complexity["advised_donation"],
        "points_spent": required_points if user.get("role") == "customer" else 0,
        "pool_status": pool_status,
        "auto_review_until": auto_review_until,
        "claimed_by": "",
        "claimed_by_id": "",
        "status_index": status_index,
        "priority": priority,
        "project_type": "Client mod",
        "assignee": assignee,
        "budget_state": "Not quoted",
        "studio_notes": "",
        "client_visible_notes": client_note,
        "created_at": now.isoformat(),
        "last_updated": now.isoformat(),
        "notes": client_note,
    }
    records.append(record)
    save_requests(records)
    if user.get("role") == "customer":
        users = load_users()
        for saved in users:
            if saved["id"] == user["id"]:
                saved["account_points"] = millipoints(saved.get("account_points", 0) - required_points)
                saved.setdefault("point_spend_log", []).append(
                    {
                        "id": f"spend_{secrets.token_hex(5)}",
                        "reference": reference,
                        "points": required_points,
                        "created_at": now.isoformat(),
                    }
                )
                spend_id = saved["point_spend_log"][-1]["id"]
                saved.setdefault("point_transactions", []).insert(
                    0,
                    {
                        "id": f"debit_{spend_id}",
                        "type": "debit",
                        "source": "request",
                        "label": "Mod request submission",
                        "points": required_points,
                        "hours": 0,
                        "reference": reference,
                        "note": f"Points deducted for {record['project_name']}.",
                        "created_at": now.isoformat(),
                        "balance_after": saved["account_points"],
                    },
                )
                session["account"] = public_user(saved)
                break
        save_users(users)
    destination = request.form.get("destination", "detail")
    if destination == "client":
        return redirect(url_for("client_portal", tab="Requests"))
    return redirect(url_for("request_detail", reference=reference))


@app.get("/requests/<reference>")
def request_detail(reference):
    record = find_record(reference)
    if not record:
        return render_template("not_found.html", reference=reference), 404
    account = current_user()
    timer_running = any(
        entry.get("user_id") == account.get("id") and not entry.get("end")
        for entry in record.get("time_entries", [])
    )
    return render_template(
        "request.html",
        record=record,
        phases=PHASES,
        progress=task_progress(record),
        can_manage_tasks=account.get("role") in STAFF_ROLES,
        tracked_hours=total_tracked_hours(record),
        timer_running=timer_running,
    )


@app.get("/api/requests/<reference>")
def request_lookup(reference):
    record = find_record(reference)
    if not record:
        return jsonify({"error": "Reference not found"}), 404
    return jsonify({"record": record, "phases": PHASES})


def find_record(reference):
    normalized = reference.strip().upper()
    for record in load_requests():
        if record["reference"].upper() == normalized:
            return record
    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

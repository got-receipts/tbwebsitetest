import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REQUESTS_FILE = DATA_DIR / "requests.json"
USERS_FILE = DATA_DIR / "users.json"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))


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

WORKSHOP_DEPENDENCIES = [
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
]

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
STUDIO_TABS = ["Command", "Projects", "Pipeline", "Clients", "Complexity", "Settings", "Admin"]
CLIENT_TABS = ["Overview", "Requests", "New Build", "Account"]
ROLES = ["customer", "developer", "admin"]
TEST_ACCOUNTS = [
    {
        "username": "admin_test",
        "email": "admin@thunderbuddies.test",
        "password": "ThunderAdmin123!",
        "role": "admin",
    },
    {
        "username": "client_test",
        "email": "client@thunderbuddies.test",
        "password": "ThunderClient123!",
        "role": "customer",
    },
]


def ensure_storage():
    DATA_DIR.mkdir(exist_ok=True)
    if not REQUESTS_FILE.exists():
        REQUESTS_FILE.write_text("[]", encoding="utf-8")
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")
    seed_test_accounts()


def seed_test_accounts():
    users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    existing = {user.get("email", "").lower() for user in users}
    changed = False

    for account in TEST_ACCOUNTS:
        if account["email"] in existing:
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
            }
        )
        changed = True

    if changed:
        USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def load_requests():
    ensure_storage()
    records = json.loads(REQUESTS_FILE.read_text(encoding="utf-8"))
    return [normalize_record(record) for record in records]


def save_requests(records):
    ensure_storage()
    REQUESTS_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")


def load_users():
    ensure_storage()
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def save_users(users):
    ensure_storage()
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def public_user(user):
    return {key: value for key, value in user.items() if key != "password_hash"}


def find_user(identifier):
    normalized = identifier.strip().lower()
    for user in load_users():
        if user.get("email", "").lower() == normalized or user.get("username", "").lower() == normalized:
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
    }
    users.append(user)
    save_users(users)
    return user


def access_code_allows(role, code):
    if role == "customer":
        return True
    env_name = "ADMIN_ACCESS_CODE" if role == "admin" else "DEVELOPER_ACCESS_CODE"
    expected = os.environ.get(env_name)
    if expected:
        return secrets.compare_digest(code or "", expected)
    fallback = "THUNDERADMIN" if role == "admin" else "THUNDERDEV"
    return secrets.compare_digest(code or "", fallback)


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
    return record


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
        "avg_complexity": round(total_complexity / len(active)) if active else 0,
        "by_phase": by_phase,
        "module_counts": sorted(module_counts.items(), key=lambda item: item[1], reverse=True),
    }


def client_metrics(records):
    active = [record for record in records if record.get("status_index", 0) < len(PHASES) - 1]
    review = [record for record in records if record.get("status_index", 0) == 5]
    return {
        "total": len(records),
        "active": len(active),
        "review": len(review),
        "completed": len(records) - len(active),
    }


def calculate_complexity(form):
    score = 0
    selected = []
    selected_build_options = []
    selected_dependencies = []

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
            score += option["points"]
            selected_build_options.append(
                {
                    "group": group["title"],
                    "id": option["id"],
                    "label": option["label"],
                    "points": option["points"],
                }
            )

    for dependency in WORKSHOP_DEPENDENCIES:
        if form.get(f"dep_{dependency['id']}") != "on":
            continue
        score += dependency["points"]
        selected_dependencies.append(dependency)

    custom_description = form.get("custom_description", "").strip()
    if form.get("custom_enabled") == "on" and custom_description:
        detail_points = min(24, max(8, len(custom_description.split()) // 6))
        score += detail_points
        selected_build_options.append(
            {
                "group": "Custom",
                "id": "custom_notes",
                "label": "Custom request notes",
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

    return {
        "score": score,
        "tier": complexity_tier(score),
        "selected_modules": selected,
        "selected_build_options": selected_build_options,
        "selected_dependencies": selected_dependencies,
        "deadline_points": deadline_points,
    }


def current_user():
    account = session.get("account")
    if account:
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
    return current_user().get("role") in {"developer", "admin"}


def admin_unlocked():
    return current_user().get("role") == "admin"


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
        return redirect(url_for("studio_dashboard", tab="Admin"))
    if role == "developer":
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

    return render_template(
        "client.html",
        user=user,
        records=records,
        metrics=client_metrics(records),
        phases=PHASES,
        modules=MODULES,
        build_option_groups=BUILD_OPTION_GROUPS,
        workshop_dependencies=WORKSHOP_DEPENDENCIES,
        tabs=CLIENT_TABS,
        active_tab=active_tab,
    )


@app.get("/logout")
def logout():
    session.pop("account", None)
    session.pop("discord_user", None)
    return redirect(url_for("home"))


@app.get("/studio/login")
def studio_login():
    return redirect(url_for("login", next="/studio"))


@app.post("/studio/login")
def studio_login_post():
    return redirect(url_for("login", next="/studio"))


@app.get("/studio/logout")
def studio_logout():
    session.pop("account", None)
    return redirect(url_for("home"))


@app.get("/studio")
def studio_dashboard():
    account = current_user()
    records = sort_records(load_requests())
    query = request.args.get("q", "").strip().lower()
    active_tab = request.args.get("tab", "Command")
    visible_tabs = STUDIO_TABS if account.get("role") == "admin" else [tab for tab in STUDIO_TABS if tab != "Admin"]
    if active_tab not in visible_tabs:
        active_tab = "Command"

    if query:
        records = [
            record
            for record in records
            if query in record.get("reference", "").lower()
            or query in record.get("project_name", "").lower()
            or query in record.get("discord_name", "").lower()
            or query in record.get("unit_name", "").lower()
        ]

    return render_template(
        "studio.html",
        records=records,
        metrics=dashboard_metrics(records),
        phases=PHASES,
        priorities=PRIORITIES,
        project_types=PROJECT_TYPES,
        tabs=visible_tabs,
        active_tab=active_tab,
        query=query,
        account=account,
        users=[public_user(user) for user in load_users()],
        is_admin=account.get("role") == "admin",
    )


@app.post("/studio/requests/<reference>/update")
def studio_update_request(reference):
    records = load_requests()
    record = next((item for item in records if item["reference"].upper() == reference.upper()), None)
    if not record:
        return render_template("not_found.html", reference=reference), 404

    status_index = int(request.form.get("status_index", record.get("status_index", 0)))
    record["status_index"] = max(0, min(status_index, len(PHASES) - 1))
    record["priority"] = request.form.get("priority", record.get("priority", "Normal"))
    record["project_type"] = request.form.get("project_type", record.get("project_type", "Client mod"))
    record["assignee"] = request.form.get("assignee", "Unassigned").strip() or "Unassigned"
    record["budget_state"] = request.form.get("budget_state", "Not quoted").strip() or "Not quoted"
    record["client_visible_notes"] = request.form.get("client_visible_notes", "").strip()
    record["studio_notes"] = request.form.get("studio_notes", "").strip()
    record["notes"] = record["client_visible_notes"] or record.get("notes", "")
    record["last_updated"] = datetime.now(timezone.utc).isoformat()

    save_requests(records)
    return redirect(url_for("studio_dashboard", tab=request.form.get("return_tab", "Projects")))


@app.get("/login/discord")
def discord_login():
    client_id = os.environ.get("DISCORD_CLIENT_ID")
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI")
    if client_id and redirect_uri:
        params = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "identify",
            }
        )
        return redirect(f"https://discord.com/api/oauth2/authorize?{params}")

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
    users = load_users()
    for saved in users:
        if saved["id"] == user["id"]:
            saved["username"] = user["username"]
    save_users(users)
    login_user(user)
    return redirect(url_for("dashboard"))


@app.get("/auth/discord/callback")
def discord_callback():
    code = request.args.get("code")
    client_id = os.environ.get("DISCORD_CLIENT_ID")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET")
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI")

    if not code or not client_id or not client_secret or not redirect_uri:
        return redirect(url_for("home"))

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
        "https://discord.com/api/oauth2/token",
        data=token_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urlopen(token_request, timeout=10) as response:
        token_payload = json.loads(response.read().decode("utf-8"))

    user_request = Request(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    with urlopen(user_request, timeout=10) as response:
        discord_user = json.loads(response.read().decode("utf-8"))

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
            user = saved
            break
    save_users(users)
    login_user(user)
    return redirect(url_for("dashboard"))


@app.post("/requests")
def create_request():
    records = load_requests()
    user = current_user()
    complexity = calculate_complexity(request.form)
    reference = make_reference(records)

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
        "status_index": 0,
        "priority": "Normal",
        "project_type": "Client mod",
        "assignee": "Unassigned",
        "budget_state": "Not quoted",
        "studio_notes": "",
        "client_visible_notes": "Request received. Thunder Buddies Studios will review scope and confirm the production lane.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "notes": "Request received. Thunder Buddies Studios will review scope and confirm the production lane.",
    }
    records.append(record)
    save_requests(records)
    destination = request.form.get("destination", "detail")
    if destination == "client":
        return redirect(url_for("client_portal", tab="Requests"))
    return redirect(url_for("request_detail", reference=reference))


@app.get("/requests/<reference>")
def request_detail(reference):
    record = find_record(reference)
    if not record:
        return render_template("not_found.html", reference=reference), 404
    return render_template("request.html", record=record, phases=PHASES)


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

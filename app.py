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


def ensure_storage():
    DATA_DIR.mkdir(exist_ok=True)
    if not REQUESTS_FILE.exists():
        REQUESTS_FILE.write_text("[]", encoding="utf-8")
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


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

    deadline = form.get("deadline", "standard")
    deadline_points = {"standard": 0, "soon": 12, "rush": 28}.get(deadline, 0)
    score += deadline_points

    if len(selected) >= 4:
        score += 16
    if len(selected) >= 6:
        score += 24

    return {
        "score": score,
        "tier": complexity_tier(score),
        "selected_modules": selected,
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

# Thunder Buddies Studios

Flask prototype for an Arma Reforger mod-build intake site.

## Features

- Discord sign-in entry point with real OAuth callback support.
- Role-based accounts for customers, developers, and admins.
- Separate client portal at `/client` for customer requests, progress, reference lookup, and account details.
- Step-by-step mod questionnaire for Arma Reforger builds.
- Complexity scoring based on selected build areas, description detail, integration risk, and deadline pressure.
- Generated reference numbers like `TBS-RF-1234`.
- Reference lookup endpoint and progress tracker.
- Full studio dashboard at `/studio` with command metrics, project tabs, pipeline board,
  client view, complexity analysis, and editable project controls.
- Animated public home page and dedicated login page with role routing.
- Railway-ready startup files.

## Local run

```powershell
python -m pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

The login router is at `http://localhost:5000/dashboard`. It sends customers to `/client`,
developers to `/studio`, and admins to `/studio?tab=Admin`.

The studio dashboard is at `http://localhost:5000/studio`. Developer and admin accounts can access it.

The client portal is at `http://localhost:5000/client`. Clients use Discord login and only
see client-safe progress notes, not internal studio notes.

## Seeded test accounts

These prototype accounts are created automatically if they do not already exist:

```text
Role: Admin
Username: admin_test
Email: admin@thunderbuddies.test
Password: ThunderAdmin123!
Dashboard: Admin Command / full studio oversight

Role: Customer
Username: client_test
Email: client@thunderbuddies.test
Password: ThunderClient123!
Dashboard: Client portal

Role: Thunder Buddies Developer
Username: tbs_dev_test
Email: tbs.dev@thunderbuddies.test
Password: ThunderDev123!
Dashboard: Developer Console / Thunder Buddies internal lane

Role: Third-party Developer
Username: partner_dev_test
Email: partner.dev@thunderbuddies.test
Password: PartnerDev123!
Dashboard: Developer Console / partner studio lane

Role: Tester
Username: tester_test
Email: tester@thunderbuddies.test
Password: ThunderTester123!
Dashboard: QA Bench

Role: Moderator
Username: moderator_test
Email: moderator@thunderbuddies.test
Password: ThunderMod123!
Dashboard: Moderator Desk

Role: General Staff
Username: staff_test
Email: staff@thunderbuddies.test
Password: ThunderStaff123!
Dashboard: General Staff Hub
```

## Account types and roles

```text
Customer
- Client portal access.
- Link Steam, sync Arma Reforger playtime points, create build requests, and track progress.

Developer
- Studio dashboard access.
- Project clocking, build notes, assigned work, freelance pool access, and personal production stats.

Thunder Buddies Developer
- Developer account with studio_name set to Thunder Buddies Studios.
- Broader production tabs for internal Thunder Buddies work.

Third-party Developer
- Developer account with a partner studio_name.
- Focused access for assigned projects, freelance pool work, and personal time tracking.

Tester
- Studio QA access.
- Pipeline, project QA, complexity review, and checklist verification workflows.

Moderator
- Studio queue/client review access.
- Client-facing notes, intake review, risk flags, and freelance pool moderation.

Admin
- Full studio control.
- User permissions, role changes, suspensions, point balances, economy stats, and all dashboards.

General Staff
- Any non-customer role with studio access.
- Uses the studio clock, project timers, role dashboard widgets, and personal stats.
```

## Railway

Set these environment variables in Railway:

```text
SECRET_KEY=your-long-random-secret
DEVELOPER_ACCESS_CODE=private-code-for-dev-account-creation
ADMIN_ACCESS_CODE=private-code-for-admin-account-creation
DISCORD_CLIENT_ID=your-discord-application-client-id
DISCORD_CLIENT_SECRET=your-discord-application-client-secret
DISCORD_REDIRECT_URI=https://your-railway-domain.up.railway.app/auth/discord/callback
```

The included `Procfile` starts the app with:

```text
web: gunicorn app:app
```

## Discord setup

1. Create an application in the Discord Developer Portal.
2. Open OAuth2 settings.
3. Add the Railway callback URL as a redirect URI.
4. Copy the client ID and client secret into Railway variables.

## Data note

Requests are currently stored in `data/requests.json`. That is fine for a prototype, but Railway's filesystem is not a long-term production database. The next production step should be moving requests and Discord users into Postgres.

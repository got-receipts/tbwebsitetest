# Thunder Buddies Studios

Flask prototype for an Arma Reforger mod-build intake site.

## Features

- Discord sign-in entry point with real OAuth callback support.
- Separate client portal at `/client` for customer requests, progress, reference lookup, and account details.
- Step-by-step mod questionnaire for Arma Reforger builds.
- Complexity scoring based on selected build areas, description detail, integration risk, and deadline pressure.
- Generated reference numbers like `TBS-RF-1234`.
- Reference lookup endpoint and progress tracker.
- Full studio dashboard at `/studio` with command metrics, project tabs, pipeline board,
  client view, complexity analysis, and editable project controls.
- Railway-ready startup files.

## Local run

```powershell
python -m pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

The studio dashboard is at `http://localhost:5000/studio`. If `STUDIO_PIN` is not set,
the dashboard opens in prototype mode.

The client portal is at `http://localhost:5000/client`. Clients use Discord login and only
see client-safe progress notes, not internal studio notes.

## Railway

Set these environment variables in Railway:

```text
SECRET_KEY=your-long-random-secret
STUDIO_PIN=your-private-studio-dashboard-pin
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

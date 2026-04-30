# Thunder Buddies Companion

Desktop companion app for Discord Rich Presence.

## Setup

1. Install Node.js.
2. Open this folder in PowerShell.
3. Run:

```powershell
npm install
```

4. In Discord Developer Portal, copy your application ID.
5. Set it before running:

```powershell
$env:DISCORD_APPLICATION_ID="your_application_id"
npm start
```

## Rich Presence asset

Upload the Thunder Buddies logo in Discord Developer Portal under Rich Presence Art Assets.
Use this asset key:

```text
thunderbuddies_logo
```

## Build Windows installer

```powershell
npm run build
```

The installer will be generated in `dist/`.

## Notes

Discord Desktop must be running locally. Browser Discord alone usually cannot provide the local IPC connection required for desktop Rich Presence.

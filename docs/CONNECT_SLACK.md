# Connect Your Slack Workspace

Follow these steps to connect this app to your existing Slack workspace.

## 1. Create the Slack app and get credentials

**Which option to choose when creating the app?**

- **From scratch** — Choose this if you prefer clicking through the UI. Then add the redirect URL and bot scopes in **OAuth & Permissions** (see steps below).
- **From a manifest** — Choose this to pre-fill the app in one go. When prompted for the manifest, paste the YAML below (replace `YOUR_BACKEND_URL` with `http://localhost:8000` if you run locally).

```yaml
display_information:
  name: Cursor for PMs
  description: Import feedback from Slack channels into Cursor for PMs
features:
  bot_user:
    display_name: Cursor for PMs
    always_online: false
oauth_config:
  scopes:
    bot:
      - channels:history
      - channels:read
      - users:read
      - users:read.email
  redirect_urls:
    - http://localhost:8000/api/v1/slack/oauth/callback
settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```

After creating the app (either way):

1. Go to **https://api.slack.com/apps** and open your app.
2. In the app:
   - **Basic Information** → copy **Signing Secret** → this is `SLACK_SIGNING_SECRET`.
   - **OAuth & Permissions**:
     - If you chose **From scratch**: under **Redirect URLs**, add `http://localhost:8000/api/v1/slack/oauth/callback` and save. Under **Scopes** → **Bot Token Scopes**, add: `channels:history`, `channels:read`, `users:read`, `users:read.email`.
     - Copy **Client ID** → `SLACK_CLIENT_ID`.
     - Copy **Client Secret** → `SLACK_CLIENT_SECRET`.
   - Click **Install to Workspace** (or **Reinstall**) so the app is in your Slack workspace.

## 2. Set environment variables

In your project root, edit **`.env`** (create from `.env.example` if needed) and set:

```env
SLACK_CLIENT_ID=your_client_id_here
SLACK_CLIENT_SECRET=your_client_secret_here
SLACK_SIGNING_SECRET=your_signing_secret_here
```

Generate an encryption key for storing Slack tokens (run once, then put the output in `.env`):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `.env`:

```env
ENCRYPTION_KEY=the_generated_key_here
```

Keep **BACKEND_URL** and **FRONTEND_URL** as in `.env.example` for local dev (e.g. `http://localhost:8000` and `http://localhost:3000`).

## 3. Restart the backend

```bash
docker compose restart backend
```

## 4. Connect in the app

1. Open **http://localhost:3000** → **Settings**.
2. Click **Connect Slack**.
3. Authorize the app in Slack when redirected.
4. After redirect back, choose which channels to monitor and save.

Your existing Slack workspace is now connected; messages in selected channels will create feedback items.

# SSH Session Manager

A searchable web UI for your SSH config, served locally via a lightweight Python HTTP server.

## Files

| File | Description |
|------|-------------|
| `ssh-session-manager.py` | Backend: SSH config parsing and HTTP server |
| `index.html` | Frontend: searchable web UI (HTML, CSS, JS) |
| `ssh-session-manager.sh` | macOS wrapper to manage the server as a background process |
| `com.local.ssh-session-manager.plist` | macOS LaunchAgent for auto-start on login |

The frontend and backend are intentionally kept separate. `ssh-session-manager.py` serves `index.html` from the same directory and exposes the following API endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /api/hosts` | Returns all SSH hosts grouped by config file |
| `GET /api/hosts/<filename>` | Returns all hosts from a specific config file |
| `GET /api/config` | Returns the active `SSH_CONFIG_DIR` path |

## Config Files Spec
```
## <Description>
#ENV: <Environment>
#URL: <Button Label>::<URL>
Host <Aliases_for_host>
  HostName <IP or Hostname>
  User <UserID>
  Port <SSH Port>
  identityFile <path to private key>
```

You can add multiple `#URL:` lines before a `Host` block — each becomes a clickable button on that host's row in the UI.

**Example** 👇🏻

```
## Ansible Controller
#ENV: PROD
#URL: Grafana::https://grafana.domain.com
#URL: Kibana::https://kibana.domain.com:5601
Host ansible
  HostName ansible-master.domain.com
  User manny
  Port 22
```

### `GET /api/hosts/<filename>`

Returns the hosts defined in a specific config file within `SSH_CONFIG_DIR`. Each host includes: `name`, `hostname`, `user`, `port`, `identityFile`, `description`, and `env`.

**Example — `/api/hosts/test`:**
```json
{
  "file": "test",
  "hosts": [
    {
      "name": "my-server",
      "hostname": "192.168.1.10",
      "user": "ubuntu",
      "port": "22",
      "identityFile": "~/.ssh/id_rsa",
      "description": "Production box",
      "env": "prod"
    }
  ]
}
```

Returns `404` if the file does not exist in the config directory.

---

## Quick Start

```bash
# Start the server in the background
./ssh-session-manager.sh start

# Open in your browser
./ssh-session-manager.sh open
```

---

## Wrapper Commands

```
./ssh-session-manager.sh <command>
```

| Command | Description |
|---------|-------------|
| `start` | Start the server in the background |
| `stop` | Stop the background server |
| `restart` | Restart the background server |
| `status` | Show whether the server is running |
| `logs` | Tail the log file (Ctrl+C to exit) |
| `open` | Open `http://localhost:8822` in the browser |
| `install` | Register as a macOS LaunchAgent (auto-starts on login) |
| `uninstall` | Remove the macOS LaunchAgent |

---

## Configuration

The server is configured via environment variables, either exported in your shell or set in the plist.

| Variable | Default | Description |
|----------|---------|-------------|
| `SSH_CONFIG_DIR` | `~/.ssh/config.d` | Path to your SSH config file or directory |
| `SSH_HOSTS_PORT` | `8822` | Port the web UI is served on |

**Example — custom config path and port:**
```bash
SSH_CONFIG_DIR=~/.ssh/config SSH_HOSTS_PORT=9000 ./ssh-session-manager.sh start
```

---

## Auto-Start on Login (LaunchAgent)

To have the server start automatically every time you log in:

**Install:**
```bash
./ssh-session-manager.sh install
```

This copies the plist to `~/Library/LaunchAgents/` and loads it immediately.

**Uninstall:**
```bash
./ssh-session-manager.sh uninstall
```

> **Note:** If you move the scripts to a different directory after installing the LaunchAgent, uninstall and reinstall so the paths in the plist are updated.

### Manually editing the LaunchAgent

To change the port or config directory for the LaunchAgent, edit `com.local.ssh-session-manager.plist` before running `install`, or edit the installed copy directly:

```bash
open ~/Library/LaunchAgents/com.local.ssh-session-manager.plist
```

Then reload it:
```bash
launchctl unload ~/Library/LaunchAgents/com.local.ssh-session-manager.plist
launchctl load   ~/Library/LaunchAgents/com.local.ssh-session-manager.plist
```

---

## Logs

Logs are written to `~/Library/Logs/ssh-session-manager.log`.

```bash
# Follow live output
./ssh-session-manager.sh logs

# Or view directly
cat ~/Library/Logs/ssh-session-manager.log
```

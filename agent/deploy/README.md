# Deploy templates

Run the publisher as a background service so it survives logout/restart.

## macOS (launchd)

1. Edit `com.claudeportal.agent.plist`: replace `/Users/YOU/...` paths and the
   `FILL_ME` credentials with your Adafruit IO username and AIO key.
2. Install:
   ```bash
   cp com.claudeportal.agent.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.claudeportal.agent.plist
   ```
3. Tail logs:
   ```bash
   tail -f /tmp/claude-portal-agent.log /tmp/claude-portal-agent.err.log
   ```

## Linux (systemd, user unit)

1. Put your credentials in `~/.config/claude-portal/agent.env`:
   ```
   ADAFRUIT_IO_USERNAME=you
   ADAFRUIT_IO_KEY=...
   ```
2. Install the unit:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp claude-portal-agent.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now claude-portal-agent.service
   ```
3. Tail logs:
   ```bash
   journalctl --user -u claude-portal-agent.service -f
   ```

Adjust `WorkingDirectory` / `ExecStart` paths in the unit file to match where
you cloned the repo.

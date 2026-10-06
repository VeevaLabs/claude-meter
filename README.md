# Claude Meter

A floating macOS desktop widget showing your Claude Code spend for the current
month vs. budget, with an over/under burn-rate indicator and a per-model
breakdown.

## Requirements

- macOS
- Swift command-line tools (`xcode-select --install` if you don't have them)
- Python 3 (preinstalled on macOS)

## Install

```sh
git clone https://github.com/snstanton/claude-meter.git
cd claude-meter
./install.sh
```

This builds the app, installs the binary to `~/.local/bin/claude-meter-widget`,
and registers a LaunchAgent so it starts automatically at login. The widget
appears in the top-right corner of your screen — drag it anywhere; it
remembers its position.

## Budget data

If your Anthropic account has usage credits enabled, the widget reads the
real spend/budget straight from `~/.claude.json` (the same data the `/usage`
command in Claude Code shows), kept fresh automatically as you use Claude
Code.

Otherwise it falls back to estimating cost from local session transcripts
against a budget you set in `~/.claude-meter/config.json`:

```json
{ "budget_usd": 100 }
```

## Uninstall

```sh
launchctl unload ~/Library/LaunchAgents/com.scottstanton.claudemeter.plist
rm ~/Library/LaunchAgents/com.scottstanton.claudemeter.plist
rm ~/.local/bin/claude-meter-widget
```

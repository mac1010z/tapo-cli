# tapo-cli

Control Tapo cameras from the terminal. Live view with half-block character rendering (works in any terminal), pan/tilt, privacy mode, snapshots, and more.

> For HD rendering using the Kitty graphics protocol, see [tapokitty-cli](https://github.com/mac1010z/tapokitty-cli).

## Install

```bash
brew install mac1010z/tools/tapo-cli
```

Or with pip:

```bash
pip install tapo-cli
```

## Setup

On first run, a config file is created at `~/.config/tapo-cli/config.json`. Edit it with your camera details:

```json
{
  "cameras": {
    "living": {"ip": "192.168.1.100", "name": "Living Room"},
    "door": {"ip": "192.168.1.101", "name": "Front Door"}
  },
  "rtsp_user": "your_rtsp_user",
  "rtsp_password": "your_rtsp_password",
  "api_user": "admin",
  "api_password": "your_api_password"
}
```

## Requirements

- `ffmpeg` (for live view and snapshots)
- A Kitty-compatible terminal (for `view` command)

## Usage

```bash
tapo list                    # List configured cameras
tapo status living           # Show camera info
tapo privacy living on       # Cover the lens
tapo privacy living off      # Uncover the lens
tapo move living 10 0        # Pan right
tapo led living off          # Turn off indicator LED
tapo alarm living on         # Trigger alarm
tapo detection living on     # Enable motion detection
tapo view living             # Live stream (Kitty terminal)
tapo snap living             # Terminal snapshot
tapo preset living list      # List presets
tapo preset living go --id 1 # Go to preset
tapo reboot living           # Reboot camera
tapo config                  # Show config location
```

### Live View Controls

| Key | Action |
|-----|--------|
| q | Quit |
| : | Enter command mode |
| Tab | Switch camera |
| w/a/s/d | Pan/tilt |
| p | Toggle privacy |
| l | Toggle LED |
| ! | Toggle alarm |
| m | Toggle motion detection |

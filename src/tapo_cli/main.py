#!/usr/bin/env python3
"""CLI tool to control Tapo cameras from the terminal."""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time

from pytapo import Tapo

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "tapo-cli")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "cameras": {
        "example": {"ip": "192.168.1.100", "name": "Example Camera"}
    },
    "rtsp_user": "admin",
    "rtsp_password": "changeme",
    "api_user": "admin",
    "api_password": "changeme",
}


GUIDE = """\033[1;36m
  ╔════════════════════════════════════════════════╗
  ║            TAPO CLI — Getting Started          ║
  ╚════════════════════════════════════════════════╝\033[0m

  \033[1m1. Configure your cameras\033[0m

     Edit \033[33m~/.config/tapo-cli/config.json\033[0m with your camera details:

     {
       "cameras": {
         "living": {"ip": "192.168.1.100", "name": "Living Room"},
         "door":   {"ip": "192.168.1.101", "name": "Front Door"}
       },
       "rtsp_user": "your_rtsp_user",
       "rtsp_password": "your_rtsp_password",
       "api_user": "admin",
       "api_password": "your_tapo_cloud_password"
     }

     \033[2mYou can find camera IPs in your router's admin page or the Tapo app.\033[0m

  \033[1m2. Requirements\033[0m

     • ffmpeg (for live view & snapshots): \033[33mbrew install ffmpeg\033[0m
     • A Kitty-compatible terminal (for the \033[33mview\033[0m command)

  \033[1m3. Usage\033[0m

     \033[33mtapo list\033[0m                     List configured cameras
     \033[33mtapo status <cam>\033[0m             Show camera info
     \033[33mtapo privacy <cam> on|off\033[0m     Cover/uncover lens
     \033[33mtapo move <cam> <x> <y>\033[0m       Pan/tilt
     \033[33mtapo view <cam>\033[0m               Live stream (Kitty terminal)
     \033[33mtapo snap <cam>\033[0m               Terminal snapshot
     \033[33mtapo led <cam> on|off\033[0m         Toggle indicator LED
     \033[33mtapo alarm <cam> on|off\033[0m       Trigger/stop alarm
     \033[33mtapo detection <cam> on|off\033[0m   Toggle motion detection
     \033[33mtapo preset <cam> list|go\033[0m     Manage presets
     \033[33mtapo reboot <cam>\033[0m             Reboot camera
     \033[33mtapo config\033[0m                   Show config file path
     \033[33mtapo guide\033[0m                    Show this guide

  \033[1m4. Live View Controls\033[0m

     \033[33mq\033[0m  Quit   \033[33m:\033[0m  Command mode   \033[33mTab\033[0m  Switch camera
     \033[33mw/a/s/d\033[0m  Pan/tilt   \033[33mp\033[0m  Privacy   \033[33ml\033[0m  LED
     \033[33m!\033[0m  Alarm   \033[33mm\033[0m  Motion detection
"""


def show_guide():
    print(GUIDE)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        show_guide()
        print(f"  \033[1;32mConfig file created at:\033[0m \033[33m{CONFIG_FILE}\033[0m")
        print(f"  Edit it with your camera details, then run \033[33mtapo list\033[0m to verify.\n")
        sys.exit(0)
    with open(CONFIG_FILE) as f:
        return json.load(f)


CONFIG = None
CAMERAS = None


def cfg():
    global CONFIG, CAMERAS
    if CONFIG is None:
        CONFIG = load_config()
        CAMERAS = CONFIG["cameras"]
    return CONFIG


def get_camera(name):
    c = cfg()
    if name not in CAMERAS:
        print(f"Unknown camera '{name}'. Available: {', '.join(CAMERAS.keys())}")
        sys.exit(1)
    cam = CAMERAS[name]
    return Tapo(cam["ip"], c["api_user"], c["api_password"])


def cmd_status(args):
    c = cfg()
    tapo = get_camera(args.camera)
    info = tapo.getBasicInfo()
    basic = info["device_info"]["basic_info"]
    print(f"Camera:    {CAMERAS[args.camera]['name']}")
    print(f"IP:        {CAMERAS[args.camera]['ip']}")
    print(f"Device:    {basic.get('device_model', 'N/A')}")
    print(f"Firmware:  {basic.get('sw_version', 'N/A')}")
    print(f"On:        {basic.get('device_info', {}).get('status', 'N/A')}")


def cmd_privacy(args):
    c = cfg()
    tapo = get_camera(args.camera)
    if args.state == "on":
        tapo.setPrivacyMode(True)
        print(f"{CAMERAS[args.camera]['name']}: Privacy mode ON (lens covered)")
    else:
        tapo.setPrivacyMode(False)
        print(f"{CAMERAS[args.camera]['name']}: Privacy mode OFF (lens active)")


def cmd_move(args):
    cfg()
    tapo = get_camera(args.camera)
    tapo.moveMotor(args.x, args.y)
    print(f"{CAMERAS[args.camera]['name']}: Moving to ({args.x}, {args.y})")


def cmd_preset(args):
    cfg()
    tapo = get_camera(args.camera)
    if args.action == "list":
        presets = tapo.getPresets()
        if not presets:
            print("No presets saved.")
        else:
            for pid, name in presets.items():
                print(f"  [{pid}] {name}")
    elif args.action == "go":
        if args.id is None:
            print("Error: --id required for 'go' action")
            sys.exit(1)
        tapo.setPreset(args.id)
        print(f"{CAMERAS[args.camera]['name']}: Moving to preset {args.id}")


def cmd_led(args):
    cfg()
    tapo = get_camera(args.camera)
    if args.state == "on":
        tapo.setIndicatorLightMode(True)
        print(f"{CAMERAS[args.camera]['name']}: LED indicator ON")
    else:
        tapo.setIndicatorLightMode(False)
        print(f"{CAMERAS[args.camera]['name']}: LED indicator OFF")


def cmd_alarm(args):
    cfg()
    tapo = get_camera(args.camera)
    if args.state == "on":
        tapo.startManualAlarm()
        print(f"{CAMERAS[args.camera]['name']}: Alarm started")
    else:
        tapo.stopManualAlarm()
        print(f"{CAMERAS[args.camera]['name']}: Alarm stopped")


def cmd_detection(args):
    cfg()
    tapo = get_camera(args.camera)
    if args.state == "on":
        tapo.setMotionDetection(True)
        print(f"{CAMERAS[args.camera]['name']}: Motion detection ON")
    else:
        tapo.setMotionDetection(False)
        print(f"{CAMERAS[args.camera]['name']}: Motion detection OFF")


def cmd_view(args):
    import select
    import termios
    import threading
    import tty

    c = cfg()
    cam = CAMERAS[args.camera]
    current_cam = args.camera
    rtsp_url = f"rtsp://{c['rtsp_user']}:{c['rtsp_password']}@{cam['ip']}:554/stream1"
    cols, rows = shutil.get_terminal_size()

    CHEATSHEET = [
        "TAPO LIVE VIEW",
        "──────────────────────",
        "q        Quit",
        ":        Enter command",
        "Tab      Switch camera",
        "a/d      Pan left/right",
        "w/s      Tilt up/down",
        "p        Privacy toggle",
        "l        LED toggle",
        "!        Alarm toggle",
        "m        Motion detect toggle",
        "──────────────────────",
        "Commands (after :)",
        "  move <x> <y>",
        "  preset list",
        "  preset go <id>",
        "  reboot",
        "  snap",
    ]

    privacy_on = False
    led_on = True
    detection_on = True
    alarm_on = False
    cmd_input = ""
    cmd_mode = False
    status_msg = f"Streaming {CAMERAS[current_cam]['name']}..."
    status_time = time.time()
    ffmpeg_proc = None
    tapo_conn = None
    tapo_retry_after = 0

    def run_cmd(fn):
        def wrapper():
            try:
                fn()
            except Exception as e:
                set_status(f"Error: {e}")
        threading.Thread(target=wrapper, daemon=True).start()

    def ensure_tapo():
        nonlocal tapo_conn, tapo_retry_after
        if tapo_conn is not None:
            return tapo_conn
        now = time.time()
        if now < tapo_retry_after:
            remaining = int(tapo_retry_after - now)
            set_status(f"Suspended, retry in {remaining}s")
            return None
        try:
            tapo_conn = Tapo(CAMERAS[current_cam]["ip"], c["api_user"], c["api_password"])
            return tapo_conn
        except Exception as e:
            msg = str(e)
            if "Try again in" in msg:
                try:
                    secs = int(msg.split("Try again in")[1].split("seconds")[0].strip())
                    tapo_retry_after = now + secs
                    set_status(f"Suspended, retry in {secs}s")
                except Exception:
                    set_status(f"Error: {msg}")
            else:
                set_status(f"Error: {msg}")
            return None

    old_settings = termios.tcgetattr(sys.stdin)

    def set_status(msg):
        nonlocal status_msg, status_time
        status_msg = msg
        status_time = time.time()

    def get_capture_size():
        c, r = shutil.get_terminal_size()
        return c, (r - 2) * 2  # 2 pixel rows per terminal row, minus status bar

    CAPTURE_W, CAPTURE_H = get_capture_size()

    def start_ffmpeg(url):
        nonlocal ffmpeg_proc, CAPTURE_W, CAPTURE_H
        if ffmpeg_proc:
            ffmpeg_proc.kill()
            ffmpeg_proc.wait()
        CAPTURE_W, CAPTURE_H = get_capture_size()
        ffmpeg_proc = subprocess.Popen(
            [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", url,
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "-s", f"{CAPTURE_W}x{CAPTURE_H}",
                "-r", "10",
                "-loglevel", "quiet",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return ffmpeg_proc

    latest_frame = None
    frame_lock = threading.Lock()
    reader_running = True

    def frame_reader_thread():
        nonlocal latest_frame, ffmpeg_proc
        while reader_running:
            proc = ffmpeg_proc
            if proc is None or proc.poll() is not None:
                time.sleep(0.1)
                continue
            frame_size = CAPTURE_W * CAPTURE_H * 3
            try:
                data = proc.stdout.read(frame_size)
                if data and len(data) == frame_size:
                    with frame_lock:
                        latest_frame = data
            except Exception:
                time.sleep(0.1)

    def render_frame(raw):
        nonlocal cols, rows
        cols, rows = shutil.get_terminal_size()
        w = CAPTURE_W
        h = CAPTURE_H

        buf = ["\033[H"]  # move to top-left

        for ty in range(h // 2):
            top_y = ty * 2
            bot_y = ty * 2 + 1
            row = []
            for x in range(w):
                ti = (top_y * w + x) * 3
                bi = (bot_y * w + x) * 3
                tr, tg, tb = raw[ti], raw[ti+1], raw[ti+2]
                if bot_y < h:
                    br, bg, bb = raw[bi], raw[bi+1], raw[bi+2]
                else:
                    br, bg, bb = 0, 0, 0
                row.append(f"\033[48;2;{tr};{tg};{tb};38;2;{br};{bg};{bb}m\u2584")
            buf.append("".join(row) + "\033[0m")

        # status bar
        if cmd_mode:
            prompt_text = f" :{cmd_input}_"
            right_text = f"{status_msg} "
            padding = max(0, cols - len(prompt_text) - len(right_text))
            buf.append(f"\033[48;2;40;40;40;38;2;0;255;200m{prompt_text}" + " " * padding + f"\033[38;2;180;180;180m{right_text}\033[0m")
        else:
            cam_label = f" [{current_cam.upper()}] {CAMERAS[current_cam]['name']}"
            elapsed = time.time() - status_time
            msg = status_msg if elapsed < 3 else ""
            padding = max(0, cols - len(cam_label) - len(msg) - 1)
            buf.append(f"\033[48;2;40;40;40;38;2;0;255;200m{cam_label}\033[38;2;180;180;180m" + " " * padding + f"{msg} \033[0m")

        sys.stdout.write("\n".join(buf))
        sys.stdout.flush()

    def execute_cmd(cmd_str):
        nonlocal current_cam, rtsp_url, privacy_on, led_on, detection_on, alarm_on, ffmpeg_proc, tapo_conn
        parts = cmd_str.strip().split()
        if not parts:
            return

        action = parts[0]
        try:
            if action == "switch" and len(parts) == 2 and parts[1] in CAMERAS:
                current_cam = parts[1]
                rtsp_url = f"rtsp://{c['rtsp_user']}:{c['rtsp_password']}@{CAMERAS[current_cam]['ip']}:554/stream2"
                tapo_conn = None
                tapo_retry_after = 0
                start_ffmpeg(rtsp_url)
                set_status(f"Switched to {CAMERAS[current_cam]['name']}")
                return

            tc = ensure_tapo()
            if not tc:
                return

            if action == "move" and len(parts) == 3:
                tc.moveMotor(int(parts[1]), int(parts[2]))
                set_status(f"Moving to ({parts[1]}, {parts[2]})")
            elif action == "preset" and len(parts) >= 2:
                if parts[1] == "list":
                    presets = tc.getPresets()
                    if presets:
                        names = ", ".join(f"[{k}]{v}" for k, v in presets.items())
                        set_status(f"Presets: {names}")
                    else:
                        set_status("No presets")
                elif parts[1] == "go" and len(parts) == 3:
                    tc.setPreset(parts[2])
                    set_status(f"Going to preset {parts[2]}")
            elif action == "reboot":
                tc.reboot()
                set_status("Rebooting camera...")
            else:
                set_status(f"Unknown: {cmd_str}")
        except Exception as e:
            set_status(f"Error: {e}")

    try:
        tty.setraw(sys.stdin.fileno())
        sys.stdout.write("\033[?25l")
        sys.stdout.write("\033[2J")

        start_ffmpeg(rtsp_url)

        reader = threading.Thread(target=frame_reader_thread, daemon=True)
        reader.start()

        while True:
            frame = None
            with frame_lock:
                if latest_frame:
                    frame = latest_frame

            if frame:
                render_frame(frame)

            while select.select([sys.stdin], [], [], 0.03)[0]:
                ch = sys.stdin.read(1)

                if cmd_mode:
                    if ch == "\r" or ch == "\n":
                        cmd_mode = False
                        cmd_copy = cmd_input
                        cmd_input = ""
                        run_cmd(lambda: execute_cmd(cmd_copy))
                    elif ch == "\x1b":
                        cmd_mode = False
                        cmd_input = ""
                        set_status("")
                    elif ch == "\x7f":
                        cmd_input = cmd_input[:-1]
                    else:
                        cmd_input += ch
                else:
                    if ch == "q":
                        raise KeyboardInterrupt
                    elif ch == ":":
                        cmd_mode = True
                        cmd_input = ""
                    elif ch == "\t":
                        cams = list(CAMERAS.keys())
                        idx = (cams.index(current_cam) + 1) % len(cams)
                        current_cam = cams[idx]
                        rtsp_url = f"rtsp://{c['rtsp_user']}:{c['rtsp_password']}@{CAMERAS[current_cam]['ip']}:554/stream2"
                        tapo_conn = None
                        tapo_retry_after = 0
                        start_ffmpeg(rtsp_url)
                        set_status(f"Switched to {CAMERAS[current_cam]['name']}")
                    elif ch in ("a", "d", "w", "s"):
                        tc = ensure_tapo()
                        if tc:
                            dx = {"a": -10, "d": 10}.get(ch, 0)
                            dy = {"w": 10, "s": -10}.get(ch, 0)
                            labels = {"a": "Pan left", "d": "Pan right", "w": "Tilt up", "s": "Tilt down"}
                            set_status(labels[ch])
                            run_cmd(lambda dx=dx, dy=dy: tc.moveMotor(dx, dy))
                    elif ch == "p":
                        tc = ensure_tapo()
                        if tc:
                            privacy_on = not privacy_on
                            set_status(f"Privacy {'ON' if privacy_on else 'OFF'}")
                            run_cmd(lambda: tc.setPrivacyMode(privacy_on))
                    elif ch == "l":
                        tc = ensure_tapo()
                        if tc:
                            led_on = not led_on
                            set_status(f"LED {'ON' if led_on else 'OFF'}")
                            run_cmd(lambda: tc.setIndicatorLightMode(led_on))
                    elif ch == "!":
                        tc = ensure_tapo()
                        if tc:
                            alarm_on = not alarm_on
                            set_status(f"Alarm {'ON' if alarm_on else 'OFF'}")
                            if alarm_on:
                                run_cmd(lambda: tc.startManualAlarm())
                            else:
                                run_cmd(lambda: tc.stopManualAlarm())
                    elif ch == "m":
                        tc = ensure_tapo()
                        if tc:
                            detection_on = not detection_on
                            set_status(f"Motion detection {'ON' if detection_on else 'OFF'}")
                            run_cmd(lambda: tc.setMotionDetection(detection_on))

    except KeyboardInterrupt:
        pass
    finally:
        reader_running = False
        if ffmpeg_proc:
            ffmpeg_proc.kill()
            ffmpeg_proc.wait()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?25h")
        sys.stdout.write("\033[2J\033[H")
        print("Stream stopped.")


def cmd_snap(args):
    try:
        from PIL import Image
    except ImportError:
        print("Pillow is required for snap. Install it: pip install Pillow")
        sys.exit(1)

    c = cfg()
    cam = CAMERAS[args.camera]
    rtsp_url = f"rtsp://{c['rtsp_user']}:{c['rtsp_password']}@{cam['ip']}:554/stream1"
    cols, rows = shutil.get_terminal_size()
    width = cols
    height = (rows - 2) * 2

    proc = subprocess.run(
        [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-frames:v", "1",
            "-f", "image2pipe",
            "-vcodec", "bmp",
            "-loglevel", "quiet",
            "pipe:1",
        ],
        capture_output=True,
        timeout=10,
    )
    if proc.returncode != 0:
        print("Failed to grab frame from camera.")
        sys.exit(1)

    img = Image.open(io.BytesIO(proc.stdout))
    img = img.resize((width, height))
    img = img.convert("RGB")
    pixels = img.load()

    for ty in range(height // 2):
        top_y = ty * 2
        bot_y = ty * 2 + 1
        row = []
        for x in range(width):
            tr, tg, tb = pixels[x, top_y]
            br, bg, bb = pixels[x, bot_y] if bot_y < height else (0, 0, 0)
            row.append(f"\033[48;2;{tr};{tg};{tb};38;2;{br};{bg};{bb}m\u2584")
        print("".join(row) + "\033[0m")


def cmd_reboot(args):
    cfg()
    tapo = get_camera(args.camera)
    tapo.reboot()
    print(f"{CAMERAS[args.camera]['name']}: Rebooting...")


def cmd_list(args):
    cfg()
    print("Available cameras:")
    for key, cam in CAMERAS.items():
        print(f"  {key:10s}  {cam['ip']:18s}  {cam['name']}")


def cmd_guide(args):
    show_guide()


def cmd_config(args):
    """Show config file location or open it."""
    print(f"Config file: {CONFIG_FILE}")
    if not os.path.exists(CONFIG_FILE):
        print("Run any command to generate a default config.")


def main():
    parser = argparse.ArgumentParser(
        prog="tapo",
        description="Control Tapo cameras from the terminal",
    )
    sub = parser.add_subparsers(dest="command")

    # guide
    p = sub.add_parser("guide", help="Show setup guide")
    p.set_defaults(func=cmd_guide)

    # config
    p = sub.add_parser("config", help="Show config file location")
    p.set_defaults(func=cmd_config)

    # list
    p = sub.add_parser("list", help="List available cameras")
    p.set_defaults(func=cmd_list)

    # status
    p = sub.add_parser("status", help="Show camera info")
    p.add_argument("camera")
    p.set_defaults(func=cmd_status)

    # privacy
    p = sub.add_parser("privacy", help="Toggle privacy mode (cover/uncover lens)")
    p.add_argument("camera")
    p.add_argument("state", choices=["on", "off"])
    p.set_defaults(func=cmd_privacy)

    # move
    p = sub.add_parser("move", help="Pan/tilt the camera")
    p.add_argument("camera")
    p.add_argument("x", type=int, help="Horizontal (-1 to 1)")
    p.add_argument("y", type=int, help="Vertical (-1 to 1)")
    p.set_defaults(func=cmd_move)

    # preset
    p = sub.add_parser("preset", help="Manage camera presets")
    p.add_argument("camera")
    p.add_argument("action", choices=["list", "go"])
    p.add_argument("--id", type=str, help="Preset ID for 'go' action")
    p.set_defaults(func=cmd_preset)

    # led
    p = sub.add_parser("led", help="Toggle indicator LED")
    p.add_argument("camera")
    p.add_argument("state", choices=["on", "off"])
    p.set_defaults(func=cmd_led)

    # alarm
    p = sub.add_parser("alarm", help="Trigger or stop manual alarm")
    p.add_argument("camera")
    p.add_argument("state", choices=["on", "off"])
    p.set_defaults(func=cmd_alarm)

    # detection
    p = sub.add_parser("detection", help="Toggle motion detection")
    p.add_argument("camera")
    p.add_argument("state", choices=["on", "off"])
    p.set_defaults(func=cmd_detection)

    # view
    p = sub.add_parser("view", help="Live stream from camera (Kitty terminal)")
    p.add_argument("camera")
    p.set_defaults(func=cmd_view)

    # snap
    p = sub.add_parser("snap", help="Single snapshot from camera")
    p.add_argument("camera")
    p.set_defaults(func=cmd_snap)

    # reboot
    p = sub.add_parser("reboot", help="Reboot the camera")
    p.add_argument("camera")
    p.set_defaults(func=cmd_reboot)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

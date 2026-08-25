"""Independent observer for a physical native-GUI launch check."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import websocket


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--ready", required=True)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--commands-file")
    args = parser.parse_args()
    if args.commands_file:
        args.command = json.loads(Path(args.commands_file).read_text(encoding="utf-8"))
    events_path = Path(args.events)
    ready_path = Path(args.ready)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.timeout
    socket = None
    with events_path.open("w", encoding="utf-8") as output:
        while time.monotonic() < deadline:
            try:
                socket = websocket.create_connection(
                    "ws://127.0.0.1:8771",
                    origin="tauri://localhost",
                    timeout=5,
                    enable_multithread=True,
                )
                break
            except Exception:
                time.sleep(0.5)
        if socket is None:
            return 2
        socket.settimeout(1.0)
        ready_at = None
        command_index = 0
        next_command_at = None
        awaiting_end = False
        try:
            while time.monotonic() < deadline:
                if ready_at is not None and command_index < len(args.command) and not awaiting_end:
                    if next_command_at is not None and time.monotonic() >= next_command_at:
                        text = args.command[command_index]
                        socket.send(json.dumps({"type": "command", "text": text}, ensure_ascii=False))
                        marker = {"received_at": time.time(), "message": {"type": "physical_command_sent", "text": text}}
                        output.write(json.dumps(marker, ensure_ascii=False) + "\n")
                        output.flush()
                        command_index += 1
                        awaiting_end = True
                try:
                    raw = socket.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                if not raw:
                    break
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                record = {"received_at": time.time(), "message": message}
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                output.flush()
                if message.get("type") == "runtime_status" and message.get("ready") is True:
                    if ready_at is None:
                        ready_at = time.monotonic()
                        next_command_at = ready_at + 12.0
                    ready_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
                if message.get("type") == "event" and message.get("event", {}).get("type") == "event:jarvis:end":
                    if awaiting_end:
                        awaiting_end = False
                        next_command_at = time.monotonic() + 1.0
        finally:
            socket.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

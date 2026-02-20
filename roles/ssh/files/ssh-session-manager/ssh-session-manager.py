#!/usr/bin/env python3
"""
SSH Hosts Browser — serves a searchable web UI for your SSH config.

Usage:
    SSH_CONFIG_DIR=~/.ssh/config.d ./ssh-hosts-server.py
    SSH_CONFIG_DIR=~/.ssh/config.d SSH_HOSTS_PORT=8888 python3 ssh-hosts-server.py

Environment variables:
    SSH_CONFIG_DIR  — path to directory containing SSH config files (default: ~/.ssh/config.d)
    SSH_HOSTS_PORT  — port to serve on (default: 8822)
"""

import os
import re
import json
import http.server
import socketserver
from pathlib import Path

CONFIG_DIR = os.environ.get("SSH_CONFIG_DIR", os.path.expanduser("~/.ssh/config.d"))
PORT = int(os.environ.get("SSH_HOSTS_PORT", 8822))
SCRIPT_DIR = Path(__file__).parent


def parse_ssh_config(text: str) -> list[dict]:
    hosts = []
    current = None
    pending_description = ""
    pending_env = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("##"):
            pending_description = line[2:].strip()
            continue
        if line.upper().startswith("#ENV:"):
            env_val = line[5:].strip()
            if current is not None:
                current["env"] = env_val
            else:
                pending_env = env_val
            continue
        if line.startswith("#"):
            continue
        match = re.match(r"^(\w[\w-]*)\s+(.*)", line)
        if not match:
            continue
        key, value = match.group(1).lower(), match.group(2).strip()
        if key == "host":
            names = [n for n in value.split() if "*" not in n and "?" not in n]
            for name in names:
                current = {"name": name, "hostname": "", "user": "", "port": "22", "identityFile": "", "description": pending_description, "env": pending_env}
                hosts.append(current)
            pending_description = ""
            pending_env = ""
            if not names:
                current = None
        elif current:
            if key == "hostname":
                current["hostname"] = value
            elif key == "user":
                current["user"] = value
            elif key == "port":
                current["port"] = value
            elif key == "identityfile":
                current["identityFile"] = value
    return hosts


def load_hosts_grouped() -> list[dict]:
    config_path = Path(CONFIG_DIR)
    groups = []
    seen: set[str] = set()

    def _dedup(hosts: list[dict]) -> list[dict]:
        result = []
        for h in hosts:
            if h["name"] not in seen:
                seen.add(h["name"])
                result.append(h)
        return result

    if config_path.is_file():
        hosts = _dedup(parse_ssh_config(config_path.read_text()))
        groups.append({"file": config_path.name, "hosts": hosts})
    elif config_path.is_dir():
        for filepath in sorted(config_path.iterdir()):
            if filepath.is_file() and not filepath.name.startswith("."):
                try:
                    hosts = _dedup(parse_ssh_config(filepath.read_text()))
                    if hosts:
                        groups.append({"file": filepath.name, "hosts": hosts})
                except Exception as e:
                    print(f"⚠ Skipping {filepath}: {e}")
    else:
        print(f"⚠ SSH_CONFIG_DIR '{CONFIG_DIR}' not found — serving empty host list")

    return groups


def load_all_hosts() -> list[dict]:
    all_hosts = [h for g in load_hosts_grouped() for h in g["hosts"]]
    all_hosts.sort(key=lambda h: h["name"].lower())
    return all_hosts


def load_hosts_by_file(filename: str) -> list[dict] | None:
    config_path = Path(CONFIG_DIR)
    # Reject any path traversal attempts
    if "/" in filename or "\\" in filename or filename.startswith("."):
        return None
    if config_path.is_file() and config_path.name == filename:
        return parse_ssh_config(config_path.read_text())
    elif config_path.is_dir():
        target = config_path / filename
        if target.is_file() and not target.name.startswith("."):
            try:
                return parse_ssh_config(target.read_text())
            except Exception as e:
                print(f"⚠ Error reading {target}: {e}")
    return None


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/hosts":
            self._json(load_hosts_grouped())
        elif self.path.startswith("/api/hosts/"):
            filename = self.path[len("/api/hosts/"):]
            hosts = load_hosts_by_file(filename)
            if hosts is None:
                self._error(404, f"File '{filename}' not found")
            else:
                self._json({"file": filename, "hosts": hosts})
        elif self.path == "/api/config":
            self._json({"config_dir": CONFIG_DIR})
        else:
            index = SCRIPT_DIR / "index.html"
            payload = index.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(payload))
            self.end_headers()
            self.wfile.write(payload)

    def _json(self, data):
        payload = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, code: int, message: str):
        payload = json.dumps({"error": message}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(f"  {args[0]}")


def main():
    config_path = Path(CONFIG_DIR)
    hosts = load_all_hosts()
    rows = [("config", CONFIG_DIR)]
    if config_path.is_dir():
        files = [f for f in config_path.iterdir() if f.is_file() and not f.name.startswith(".")]
        rows.append(("files", str(len(files))))
    rows.append(("hosts", str(len(hosts))))
    rows.append(("server", f"http://localhost:{PORT}"))

    label_w = max(len(k) for k, _ in rows)
    val_w   = max(len(v) for _, v in rows)
    # inner width = "  " + label + " : " + value
    inner_w = max(2 + label_w + 3 + val_w, 24)
    # expand val_w to fill inner_w exactly
    val_w   = inner_w - 2 - label_w - 3
    bar     = "─" * inner_w
    title   = "⬡  SSH Hosts Browser"

    print()
    print(f"  ┌{bar}┐")
    print(f"  │  {title}{' ' * (inner_w - 2 - len(title))}│")
    print(f"  ├{bar}┤")
    for key, val in rows:
        print(f"  │  {key:<{label_w}} : {val:<{val_w}}│")
    print(f"  └{bar}┘")
    print()

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Shutting down.")


if __name__ == "__main__":
    main()

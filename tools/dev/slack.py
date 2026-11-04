#!/usr/bin/env python3
"""Dev-only Slack CLI for testing the lab. Not used by lab agents or the final run.

Reads SLACK_USER_TOKEN from ~/.config/raccoonlabs/env and acts as that user.

  slack.py whoami
  slack.py channels
  slack.py read <channel> [limit]
  slack.py thread <channel> <ts>
  slack.py post <channel> <text> [thread_ts]
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ENV_FILE = os.path.expanduser("~/.config/raccoonlabs/env")


def token():
    if os.environ.get("SLACK_USER_TOKEN"):
        return os.environ["SLACK_USER_TOKEN"]
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith("SLACK_USER_TOKEN="):
                return line.split("=", 1)[1].strip()
    sys.exit(f"SLACK_USER_TOKEN not found in {ENV_FILE}")


def api(method, **params):
    data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(
        f"https://slack.com/api/{method}", data=data, headers={"Authorization": f"Bearer {token()}"}
    )
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                out = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(int(e.headers.get("Retry-After", "5")))
    else:
        sys.exit(f"{method}: still rate limited after 3 tries")
    if not out.get("ok"):
        sys.exit(f"{method}: {out.get('error')} {out.get('needed', '')}".strip())
    return out


def channels():
    found, cursor = [], None
    while True:
        out = api("conversations.list", types="public_channel,private_channel", limit=200,
                  exclude_archived="true", cursor=cursor)
        found += out["channels"]
        cursor = out.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return found


def channel_id(name):
    if name[0] in "CG" and name.upper() == name:
        return name
    name = name.lstrip("#")
    for c in channels():
        if c["name"] == name:
            return c["id"]
    sys.exit(f"no channel named {name} that this user can see")


def show(messages):
    for m in messages:
        who = m.get("username") or m.get("user") or m.get("bot_id") or "?"
        reply = f" [{m['reply_count']} replies]" if m.get("reply_count") else ""
        print(f"{m['ts']} {who}{reply}: {m.get('text', '')}")


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "whoami":
        out = api("auth.test")
        print(f"{out['user']} in {out['team']}")
    elif cmd == "channels":
        for c in channels():
            kind = "private" if c.get("is_private") else "public"
            print(f"{c['id']} {kind} {'member' if c.get('is_member') else '-'} #{c['name']}")
    elif cmd == "read" and len(argv) >= 2:
        limit = argv[2] if len(argv) > 2 else 20
        show(reversed(api("conversations.history", channel=channel_id(argv[1]), limit=limit)["messages"]))
    elif cmd == "thread" and len(argv) == 3:
        show(api("conversations.replies", channel=channel_id(argv[1]), ts=argv[2])["messages"])
    elif cmd == "post" and len(argv) >= 3:
        thread = argv[3] if len(argv) > 3 else None
        print(api("chat.postMessage", channel=channel_id(argv[1]), text=argv[2], thread_ts=thread)["ts"])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])

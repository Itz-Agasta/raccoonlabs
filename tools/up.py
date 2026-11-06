#!/usr/bin/env python3
"""`just up`: check this machine, build the template, and say what's left to do in Console."""
import shutil
import sys
import urllib.request

missing = [t for t in ("uv", "tectonic", "claude", "codex", "opencode") if not shutil.which(t)]
required = {"uv", "tectonic"} & set(missing)
for tool in missing:
    print(f"{'MISSING' if tool in required else 'absent (only its agent needs it)'}: {tool}")
if required:
    sys.exit("Install the missing tools, then run `just up` again.")


def server_up():
    try:
        urllib.request.urlopen("http://127.0.0.1:40401/health", timeout=3)
        return True
    except urllib.error.HTTPError:
        return True
    except OSError:
        return False


print("Tools are on PATH and switch/lab.template.yaml is built.")
print(f"Local Switch server: {'running' if server_up() else 'NOT running: open Switch Console'}")
print("""
Next, in Switch Console:
  1. Add a server > Run a server on this computer, and connect Slack.
  2. Your Agents > turn on Run managed agents on this computer.
  3. Templates > Import template > switch/lab.template.yaml, then Use > Create all.
Then back here:
  4. just harden      closes the web tools Switch's settings leave open on Scout and Reviewer 2
  5. just skills      installs the research skills and links them to the agents
Try it in Slack: address @ringtail with a question in #lab-brainstorm.""")

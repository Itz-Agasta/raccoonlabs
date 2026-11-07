default:
    @just --list

# Run the test suite
test:
    uv run pytest -q

# Put labrun on PATH for lab agents
install-tools:
    uv tool install --force --editable .

# Rebuild the Switch template from its sources
template:
    uv run python tools/dev/build_template.py

# Hash the local sealed list into the tracked blocklist
blocklist:
    uv run python tools/dev/build_blocklist.py

# Close the web tools Switch's settings leave open, in the deployed agents' folders
harden:
    uv run python tools/harden.py

# Run the whole tool chain on CPU, with no accounts, agents or GPU
demo-cpu: install-tools
    uv run python tools/demo_cpu.py

# List web and sealed-path access found in the agents' session logs
audit *ARGS:
    uv run python tools/audit.py {{ARGS}}

# Seal notes/sealed into envelope/sealed.enc (asks for the passphrase; run it in a real terminal)
seal:
    uv run lab-envelope seal notes/sealed --out envelope/sealed.enc

# Check this machine, install the lab's tools, build the template, and print the Console steps
up: install-tools template
    uv run python tools/up.py

# Install the research skills (pinned, outside this repo) and link them to the agents
skills:
    uv run python tools/setup_skills.py

# Record the whole screen for the demo (MKV survives a crash); stop with `just rec-stop`
rec-start:
    mkdir -p ~/Videos/raccoonlabs/raw
    date +%s.%N > ~/Videos/raccoonlabs/raw/start-$(date +%H%M%S).txt
    LIBVA_DRIVER_NAME=iHD setsid wf-recorder -o eDP-1 -c h264_vaapi -d /dev/dri/renderD128 -r 15 -m matroska -f ~/Videos/raccoonlabs/raw/run-$(date +%H%M%S).mkv >~/Videos/raccoonlabs/raw/wf.log 2>&1 &
    @echo "recording; mark moments with: just mark \"what happened\""

rec-stop:
    pkill -INT wf-recorder || true

# Timestamp a moment in the recording, e.g. just mark "prof approved"
mark +WHAT:
    @echo "$(date +%s.%N) {{WHAT}}" >> ~/Videos/raccoonlabs/raw/marks.txt && echo marked

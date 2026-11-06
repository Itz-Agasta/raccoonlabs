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

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

#!/bin/zsh
cd "${0:A:h}"
STUDIO_URL="http://127.0.0.1:8772"
if [[ ! -x .venv/bin/python ]]; then
  print "The studio needs its first setup. Ask Codex to set up MIT-2009-Social-Studio."
  read "?Press Return to close."
  exit 1
fi
if curl --silent --fail "$STUDIO_URL/api/library" >/dev/null; then
  open "$STUDIO_URL"
  exit 0
fi
.venv/bin/python -m mit2009_studio.server &
STUDIO_PROCESS=$!
trap 'kill "$STUDIO_PROCESS" 2>/dev/null' EXIT INT TERM
for attempt in {1..30}; do
  if curl --silent --fail "$STUDIO_URL/api/library" >/dev/null; then
    open "$STUDIO_URL"
    break
  fi
  sleep 1
done
print "Keep this window open while using 2.009 Social Studio."
wait "$STUDIO_PROCESS"

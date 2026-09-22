#!/bin/zsh
set -e
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo 'First run: follow the README to install Python 3.12+, FFmpeg, and this application.'
  echo 'Then double-click this launcher again.'
  read '?Press Return to close.'
  exit 1
fi
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
  echo 'FFmpeg is missing. Install it, then reopen the studio.'
  read '?Press Return to close.'
  exit 1
fi
(sleep 2; open 'http://127.0.0.1:8773') &
exec .venv/bin/python -m mit2009_studio.server

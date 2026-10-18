#!/usr/bin/env bash
# Хук PostToolUse (Bash): после команды, которая меняет задачи на GitHub (gh issue create/close/reopen/edit,
# gh project item-…), в фоне через 15 с — board-sync.py --all: копия канбана на досках ExcaliDash не отстаёт.
# 15 с — встроенный порядок проекта «закрыт → Готово» срабатывает на GitHub не сразу. Ничего не печатает и не мешает
# команде: код возврата всегда 0. Журнал — ~/.cache/board-sync.log; одновременно идёт один запуск (flock).
cmd=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)
if printf '%s' "$cmd" | grep -Eq 'gh +(issue +(create|close|reopen|edit|delete|transfer)|project +item-)'; then
  dir=$(dirname "$(readlink -f "$0")")
  mkdir -p ~/.cache
  ( sleep 15; flock -w 120 ~/.cache/board-sync.lock python3 "$dir/board-sync.py" --all ) >>~/.cache/board-sync.log 2>&1 </dev/null &
  disown
fi
exit 0

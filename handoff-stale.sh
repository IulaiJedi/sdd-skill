#!/usr/bin/env bash
# Хук скилла sdd: напоминает обновить живую передачу, когда она отстала от кода.
#
# Сам себя ограничивает: молчит везде, кроме git-репозитория, в котором лежит
# docs/handoff-*.md. В проектах без SDD не делает ничего.
#
# Закон хуков: любая неожиданность — тихий выход с кодом 0. Хук напоминает, а не
# мешает работать.
set -u

exit_quiet() { exit 0; }
trap exit_quiet ERR

command -v git >/dev/null 2>&1 || exit 0
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$root" ] || exit 0

# Самая свежая передача в репозитории.
doc="$(ls -t "$root"/docs/handoff-*.md 2>/dev/null | head -1)" || exit 0
[ -n "${doc:-}" ] || exit 0

# Сколько коммитов легло после последней правки передачи.
last="$(git -C "$root" log -1 --format=%H -- "$doc" 2>/dev/null)" || exit 0
[ -n "$last" ] || exit 0
behind="$(git -C "$root" rev-list --count "$last"..HEAD 2>/dev/null)" || exit 0
[ -n "$behind" ] || exit 0

# Незакоммиченная работа тоже считается: она и теряется первой.
dirty="$(git -C "$root" status --porcelain 2>/dev/null | grep -vc '^?? \.claude/' || true)"
[ -n "${dirty:-}" ] || dirty=0

THRESHOLD="${SDD_HANDOFF_THRESHOLD:-3}"
[ "$behind" -ge "$THRESHOLD" ] || exit 0

rel="${doc#"$root"/}"
printf 'Передача %s отстала: %s коммит(ов) после её последней правки, незакоммиченных файлов %s. Обнови её по ~/.claude/skills/sdd/handoff.md — состояние тикетов, ветки и рабочие копии, план на остаток, разрешения оператора. Свежая передача делает /clear и обрыв бесплатными.\n' \
    "$rel" "$behind" "$dirty"
exit 0

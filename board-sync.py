#!/usr/bin/env python3
"""Канбан GitHub Projects → раздел «Задачи — канбан» на доске ExcaliDash (доска «разработка» проекта).

Задачи живут на GitHub Projects; белая доска — их копия для глаз оператора, рядом со схемами проекта.
Каждая карточка закреплена за элементом проекта (id фигур стабильны): повторный запуск обновляет
раздел, а не рисует второй. Доска совместная и сливает фигуры по id — правка идёт той же фигурой
с версией +1, лишняя карточка помечается isDeleted (урок 04.10.2026).

Настройка — ~/.config/board-sync.json:
  { "<owner>/<repo>": { "owner": "<owner>", "project": <номер доски>, "board": "<id доски ExcaliDash>" } }
Ключ ExcaliDash — файл из EXCALIDASH_KEY_FILE (по умолчанию ~/.config/excalidash/api-key), адрес —
EXCALIDASH_URL (по умолчанию https://draw.jedicoder.store). Нужен `gh` с правом `project`.

  board-sync.py <owner/repo>        одна доска
  board-sync.py --all               все из настройки
  board-sync.py <owner/repo> --dry  посчитать и показать, ничего не писать
  board-sync.py <owner/repo> --empty  разрешить пустой канбан: без флага 0 задач при карточках на доске —
                                      сбой ответа GitHub, раздел не трогается (урок 22.10.2026)
"""
import json, os, random, subprocess, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

CONFIG = os.path.expanduser('~/.config/board-sync.json')
URL = os.environ.get('EXCALIDASH_URL', 'https://draw.jedicoder.store').rstrip('/')
KEY_FILE = os.path.expanduser(os.environ.get('EXCALIDASH_KEY_FILE', '~/.config/excalidash/api-key'))

COLUMNS = ['Идеи', 'Бэклог', 'В работе', 'Готово']
COLORS = {   # обводка, заливка карточки — как у раздела «Схема денег» на досках бизнеса
    'Идеи': ('#6b3df5', '#efeafc'), 'Бэклог': ('#d6cbf6', '#ffffff'),
    'В работе': ('#ffc83d', '#fff6db'), 'Готово': ('#00b8a4', '#e6f8f4'),
}
DONE_SHOWN = 10        # «Готово» растёт без конца — на доске последние десять, остальные — строкой «и ещё N»
COL_W, GAP, CARD_PAD = 340, 40, 12
FONT, CHARS = 16, 34   # кегль карточки и знаков в строке при ширине 340 (кириллица ~0,56 кегля)
MSK = timezone(timedelta(hours=3))


def die(msg):
    print('board-sync:', msg, file=sys.stderr)
    sys.exit(1)


def gh_items(owner, project):
    # GitHub изредка отдаёт пустой список с кодом 0 (22.10.2026 — дважды за час): пустой ответ переспрашиваем
    for attempt in range(3):
        out = subprocess.run(['gh', 'project', 'item-list', str(project), '--owner', owner, '--format', 'json', '--limit', '1000'],
                             capture_output=True, text=True)
        if out.returncode:
            die('gh project item-list: ' + out.stderr.strip()[:300])
        items = json.loads(out.stdout)['items']
        if items:
            return items
        time.sleep(5)
    return items


def gh_title(owner, project):
    out = subprocess.run(['gh', 'project', 'view', str(project), '--owner', owner, '--format', 'json'], capture_output=True, text=True)
    return json.loads(out.stdout)['title'] if out.returncode == 0 else f'проект {project}'


def api(method, path, body=None):
    key = open(KEY_FILE).read().strip()
    req = urllib.request.Request(URL + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read() or b'null')


def wrap(text, width=CHARS, lines=3):
    words, out, cur = text.split(), [], ''
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f'{cur} {w}' if cur else w
        else:
            out.append(cur)
            cur = w if len(w) <= width else w[:width - 1] + '…'
    if cur:
        out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = (out[-1][:width - 1].rstrip() + '…')
    return '\n'.join(out)


def desired(items, prefix, ox, oy, title, url):
    """Фигуры раздела: {id: свойства}. Позиции — от угла раздела (ox, oy)."""
    shapes = {}
    stamp = datetime.now(MSK).strftime('%d.%m.%Y %H:%M')
    shapes[f'{prefix}-hdr'] = text_el(ox, oy, 'Задачи — канбан', 44)
    shapes[f'{prefix}-sub'] = text_el(ox, oy + 64, f'Копия доски GitHub Projects «{title}» на {stamp} МСК. Править — там: {url}', 20, '#4f4777')
    by_col = {c: [] for c in COLUMNS}
    for it in items:
        st = it.get('status') if it.get('status') in by_col else 'Бэклог'
        by_col[st].append(it)
    for c in by_col:   # задачи по номеру, черновики — после; «Готово» — свежие сверху
        by_col[c].sort(key=lambda i: (i['content'].get('number') is None, -(i['content'].get('number') or 0) if c == 'Готово' else (i['content'].get('number') or 0)))
    for ci, col in enumerate(COLUMNS):
        x, y = ox + ci * (COL_W + GAP), oy + 120
        cards = by_col[col]
        shown = cards[:DONE_SHOWN] if col == 'Готово' else cards
        stroke, fill = COLORS[col]
        shapes[f'{prefix}-col{ci}-r'] = rect_el(x, y, COL_W, 52, stroke, fill)
        shapes[f'{prefix}-col{ci}-t'] = text_el(x + 16, y + 12, f'{col} · {len(cards)}', 22)
        cy = y + 64
        for it in shown:
            c = it['content']
            label = f"#{c['number']} {c['title']}" if c.get('number') else f"• {c['title']}"
            body = wrap(label)
            h = body.count('\n') * FONT * 1.25 + FONT * 1.25 + CARD_PAD * 2
            key = it['id'].split('_')[-1][-12:]
            shapes[f'{prefix}-{key}-r'] = rect_el(x, cy, COL_W, h, stroke, fill)
            shapes[f'{prefix}-{key}-t'] = text_el(x + CARD_PAD, cy + CARD_PAD, body, FONT)
            cy += h + 10
        if len(cards) > len(shown):
            shapes[f'{prefix}-more{ci}'] = text_el(x + 4, cy + 2, f'и ещё {len(cards) - len(shown)} — на GitHub', FONT, '#4f4777')
    return shapes


def text_el(x, y, text, size, color='#1d1640'):
    lines = text.split('\n')
    return {'type': 'text', 'x': x, 'y': y, 'width': round(max(len(l) for l in lines) * size * 0.56, 2),
            'height': round(len(lines) * size * 1.25, 2), 'strokeColor': color, 'backgroundColor': 'transparent',
            'text': text, 'originalText': text, 'fontSize': size}


def rect_el(x, y, w, h, stroke, fill):
    return {'type': 'rectangle', 'x': x, 'y': y, 'width': w, 'height': round(h, 2), 'strokeColor': stroke, 'backgroundColor': fill}


def full(el_id, props, index):
    base = {'id': el_id, 'angle': 0, 'fillStyle': 'solid', 'strokeWidth': 2, 'strokeStyle': 'solid', 'roughness': 0, 'opacity': 100,
            'groupIds': [], 'frameId': None, 'boundElements': [], 'link': None, 'locked': False, 'isDeleted': False,
            'seed': random.randrange(1, 2 ** 31), 'version': 1, 'versionNonce': random.randrange(1, 2 ** 31),
            'updated': int(time.time() * 1000), 'index': index,
            'roundness': {'type': 3} if props['type'] == 'rectangle' else None}
    if props['type'] == 'text':
        base.update({'fontFamily': 2, 'textAlign': 'left', 'verticalAlign': 'top', 'containerId': None, 'lineHeight': 1.25, 'autoResize': True})
    base.update(props)
    return base


B62 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'


def next_indexes(existing):
    """Дробные индексы после самого старшего на доске: «a0…az» → «b00…» → «c000…»."""
    top = max((i for i in existing if i), default='a0')
    head = top[0]
    width = ord(head) - ord('a') + 1
    n = 0
    for ch in top[1:1 + width]:
        n = n * 62 + B62.index(ch)
    while True:
        n += 1
        if n >= 62 ** width:
            head, width, n = chr(ord(head) + 1), width + 1, 0
        digits, k = '', n
        for _ in range(width):
            digits = B62[k % 62] + digits
            k //= 62
        yield head + digits


def sync(repo, cfg, dry=False, allow_empty=False):
    owner, project, board = cfg['owner'], cfg['project'], cfg['board']
    prefix = f'kb{project}'
    items = gh_items(owner, project)
    title = gh_title(owner, project)
    url = f'https://github.com/users/{owner}/projects/{project}'
    d = api('GET', f'/api/drawings/{board}')
    els = d['elements'] if isinstance(d['elements'], list) else json.loads(d['elements'])
    mine = {e['id']: e for e in els if e['id'].startswith(prefix + '-')}
    others = [e for e in els if not e['id'].startswith(prefix + '-')]
    # угол раздела: где он уже стоит, иначе — под всем живым на доске
    hdr = mine.get(f'{prefix}-hdr')
    if hdr and not hdr.get('isDeleted'):
        ox, oy = hdr['x'], hdr['y']
    else:
        alive = [e for e in others if not e.get('isDeleted')]
        ox = min((e['x'] for e in alive), default=0)
        oy = max((e['y'] + e.get('height', 0) for e in alive), default=-240) + 240
    want = desired(items, prefix, ox, oy, title, url)
    live = [e for e in mine.values() if not e.get('isDeleted')]
    if not items and len(live) > len(want) and not allow_empty:
        print(f'board-sync: {repo}: GitHub отдал 0 задач, а на доске есть карточки — похоже на сбой ответа, раздел не трогаю '
              '(пустой канбан — с --empty)', file=sys.stderr)
        return
    idx = next_indexes([e.get('index') for e in els])
    out, changed, added, removed = list(others), 0, 0, 0
    keys = ('type', 'x', 'y', 'width', 'height', 'strokeColor', 'backgroundColor', 'text', 'fontSize')
    for el_id, props in want.items():
        old = mine.get(el_id)
        if old and not old.get('isDeleted') and all(old.get(k) == props.get(k) for k in keys if k in props):
            out.append(old)
            continue
        new = full(el_id, props, old.get('index') if old else next(idx))
        if old:
            new['version'] = old.get('version', 1) + 1
            new['seed'] = old.get('seed', new['seed'])
            changed += 1
        else:
            added += 1
        out.append(new)
    for el_id, old in mine.items():
        if el_id not in want:
            if not old.get('isDeleted'):
                old = dict(old, isDeleted=True, version=old.get('version', 1) + 1, versionNonce=random.randrange(1, 2 ** 31),
                           updated=int(time.time() * 1000))
                removed += 1
            out.append(old)
    print(f'{repo}: задач {len(items)}, фигур раздела {len(want)} — новых {added}, изменённых {changed}, убранных {removed}')
    if dry or not (added or changed or removed):
        return
    api('PUT', f'/api/drawings/{board}', {'name': d['name'], 'elements': out, 'appState': d.get('appState') or {},
                                         'files': d.get('files') or {}, 'collectionId': d.get('collectionId')})
    back = api('GET', f'/api/drawings/{board}')
    live = [e for e in back['elements'] if e['id'].startswith(prefix + '-') and not e.get('isDeleted')]
    if len(live) != len(want):
        die(f'{repo}: на доске {len(live)} живых фигур раздела, а задумано {len(want)}')
    print(f'{repo}: доска {URL}/editor/{board} — сверено, живых фигур раздела {len(live)}')


def main(argv):
    if not argv:
        die('укажи owner/repo или --all (см. шапку файла)')
    cfg = json.load(open(CONFIG)) if os.path.exists(CONFIG) else {}
    dry = '--dry' in argv
    repos = list(cfg) if '--all' in argv else [a for a in argv if not a.startswith('--')]
    for repo in repos:
        if repo not in cfg:
            die(f'{repo}: нет в {CONFIG}')
        sync(repo, cfg[repo], dry, '--empty' in argv)


if __name__ == '__main__':
    main(sys.argv[1:])

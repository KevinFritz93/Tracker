"""Static checks for the PWA conversion: JS balance, dangling ids, JSON, paths."""
import json
import re
import sys

src = open('index.html', encoding='utf-8').read()
problems = []


def check_js(js, base_line, label):
    i, n, line = 0, len(js), base_line
    stack, prev = [], ''
    errs = []

    def allows_regex(tok):
        if tok == '':
            return True
        if tok in (')', ']', '}'):
            return False
        if re.match(r'^[A-Za-z_$][\w$]*$', tok):
            return tok in ('return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete',
                           'void', 'throw', 'case', 'do', 'else', 'yield', 'await')
        if re.match(r'^[\d.]+$', tok):
            return False
        return True

    while i < n:
        ch = js[i]
        if ch == '\n':
            line += 1; i += 1; continue
        if ch in ' \t\r':
            i += 1; continue
        if js.startswith('//', i):
            j = js.find('\n', i); i = n if j < 0 else j; continue
        if js.startswith('/*', i):
            j = js.find('*/', i + 2)
            if j < 0:
                errs.append(f'{label}: unterminated comment line {line}'); break
            line += js.count('\n', i, j); i = j + 2; continue
        if ch in '"\'':
            q = ch; i += 1
            while i < n:
                if js[i] == '\\': i += 2; continue
                if js[i] == q: i += 1; break
                if js[i] == '\n':
                    errs.append(f'{label}: unterminated string line {line}'); break
                i += 1
            prev = 'STR'; continue
        if ch == '`':
            i += 1
            while i < n:
                if js[i] == '\\': i += 2; continue
                if js[i] == '\n': line += 1; i += 1; continue
                if js[i] == '`': i += 1; break
                if js.startswith('${', i):
                    stack.append(('${', line)); i += 2; break
                i += 1
            prev = 'TPL'; continue
        if ch == '/' and allows_regex(prev):
            j, cls, ok = i + 1, False, False
            while j < n:
                c = js[j]
                if c == '\\': j += 2; continue
                if c == '\n': break
                if c == '[': cls = True
                elif c == ']': cls = False
                elif c == '/' and not cls: ok = True; break
                j += 1
            if ok:
                i = j + 1
                while i < n and js[i].isalpha(): i += 1
                prev = 'REGEX'; continue
        if ch in '([{':
            stack.append((ch, line)); prev = ch; i += 1; continue
        if ch in ')]}':
            pairs = {')': '(', ']': '[', '}': '{'}
            if not stack:
                errs.append(f'{label}: unexpected {ch} line {line}'); i += 1; continue
            top, tl = stack[-1]
            if ch == '}' and top == '${':
                stack.pop(); i += 1
                while i < n:
                    if js[i] == '\\': i += 2; continue
                    if js[i] == '\n': line += 1; i += 1; continue
                    if js[i] == '`': i += 1; break
                    if js.startswith('${', i):
                        stack.append(('${', line)); i += 2; break
                    i += 1
                prev = 'TPL'; continue
            if top != pairs[ch]:
                errs.append(f'{label}: mismatched {ch} line {line} (opened {top} line {tl})')
            stack.pop(); prev = ch; i += 1; continue
        m = re.match(r'[A-Za-z_$][\w$]*|\d[\w.]*', js[i:])
        if m:
            prev = m.group(0); i += len(prev)
        else:
            prev = ch; i += 1
    if stack:
        errs.append(f'{label}: unclosed ' + ', '.join(f'{c}@{l}' for c, l in stack[:5]))
    return errs


m = re.search(r'<script>\n(.*)</script>', src, re.S)
inline = m.group(1)
problems += check_js(inline, src[:m.start(1)].count('\n') + 1, 'index.html')

sw = open('service-worker.js', encoding='utf-8').read()
problems += check_js(sw, 1, 'service-worker.js')

# ids referenced in JS must exist in the markup
ids = set(re.findall(r'\bid="([^"]+)"', src))
used = set(re.findall(r"getElementById\('([^']+)'\)", inline))
missing = sorted(used - ids)
if missing:
    problems.append(f'getElementById without markup: {missing}')

# no leftover calls to the removed storage helpers
for gone in ('saveEntries(', 'saveDays('):
    hits = [ln for ln, t in enumerate(inline.split('\n'), 1)
            if gone in t and 'Raw(' not in t]
    if hits:
        problems.append(f'leftover {gone} at lines {hits}')

# manifest must be valid JSON with relative paths
mf = json.load(open('manifest.json', encoding='utf-8'))
for key, val in [('start_url', mf['start_url']), ('scope', mf['scope'])]:
    if val.startswith('/'):
        problems.append(f'manifest {key} is absolute: {val}')
for icon in mf['icons']:
    if icon['src'].startswith('/'):
        problems.append(f"manifest icon absolute: {icon['src']}")

# html must not reference absolute root paths (breaks GitHub Pages project sites)
for attr in re.findall(r'(?:href|src)="(/[^/][^"]*)"', src):
    problems.append(f'absolute path in index.html: {attr}')

# every table/column the client uses should exist in the schema
schema = open('supabase-schema.sql', encoding='utf-8').read().lower()
for table in ('activities', 'day_reviews'):
    if f'create table if not exists public.{table}' not in schema:
        problems.append(f'schema missing table {table}')
for col in ('deleted_at', 'updated_at'):
    if col not in schema:
        problems.append(f'schema missing column {col}')

print('\n'.join(problems) if problems else 'all checks passed')
sys.exit(1 if problems else 0)

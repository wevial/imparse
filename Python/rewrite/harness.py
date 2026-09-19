#!/usr/bin/env python3
"""harness.py pratt|derivatives|old [--fuzz N] [--time-limit S] [-v]

Runs one parser against the spec. `pratt` loads parser_pratt.py, `derivatives` loads
parser_derivatives.py, `old` runs the
2014 parser so you can see the baseline. A parser module exposes exactly one function:

    parse(grammar, tokens) -> tree | None

`grammar` is the imparse Grammar ADT, `tokens` a list of strings (the 2014 tokenizer made them),
and the tree format is described at the top of cases.py. Python 3 stdlib only.
"""
import argparse, importlib, json, math, sys, time
import cases, oracle

sys.setrecursionlimit(60000)   # so a recursive parser fails on time, not on Python's default depth
GREEN, RED, YELLOW, DIM, OFF = ('\033[32m', '\033[31m', '\033[33m', '\033[2m', '\033[0m') if sys.stdout.isatty() else ('',) * 5

def show(t):
    return json.dumps(t, separators=(',', ':')) if t is not None else 'None'

def load(which):
    if which == 'old':
        return oracle.parse
    return importlib.import_module('parser_' + which).parse

def run(parse, grammar, src, limit):
    tokens = oracle.tokenize(grammar, src) if src else []
    return oracle.run_with_timeout(lambda: parse(grammar, tokens), limit)

def section(title):
    print('\n' + title + '\n' + '-' * len(title))

def check(parse, items, limit, verbose, label):
    ok = 0
    for grammar, src, want in items:
        got, err = run(parse, grammar, src, limit)
        good = err is None and got == want
        ok += good
        if not good or verbose:
            mark = GREEN + 'ok  ' + OFF if good else RED + 'FAIL' + OFF
            print('  %s %-28r' % (mark, src))
            if not good:
                print('       want %s\n       got  %s' % (show(want), err or show(got)))
    colour = GREEN if ok == len(items) else RED
    print('  %s%d / %d %s%s' % (colour, ok, len(items), label, OFF))
    return ok == len(items)

def timing(parse, limit):
    all_linear = True
    for name, grammar, make in cases.TIMING:
        pts, n, note = [], 8, ''
        while n <= 16384:
            src = make(n)
            t0 = time.perf_counter()
            got, err = run(parse, grammar, src, limit)
            dt = time.perf_counter() - t0
            if err:
                note = '%s at n=%d' % (err, n); break
            if got is None:
                note = 'returned None at n=%d' % n; break
            pts.append((n, dt)); n *= 2
        usable = [(a, b) for a, b in pts if b > 2e-3]
        if len(usable) >= 3:     # least-squares slope of log t against log n
            xs, ys = [math.log(a) for a, _ in usable], [math.log(b) for _, b in usable]
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            k = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
            verdict = 'n^%.2f' % k
            colour = GREEN if k < 1.35 and not note else YELLOW if k < 3.3 and not note else RED
        else:
            verdict, colour = ('too fast to fit' if not note else 'no curve'), (GREEN if not note else RED)
        all_linear &= colour == GREEN
        reach = pts[-1] if pts else (0, 0)
        print('  %s%-38s %-16s%s reached n=%-6d in %.3fs  %s' % (colour, name, verdict, OFF, reach[0], reach[1], DIM + note + OFF))
    return all_linear

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('which', choices=['pratt', 'derivatives', 'old'])
    ap.add_argument('--fuzz', type=int, default=300)
    ap.add_argument('--time-limit', type=float, default=3.0, help='seconds per single parse')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    try:
        parse = load(a.which)
        parse(cases.SPEC[0][0], ['true'])
    except NotImplementedError as e:
        print('parser_%s.parse is still the stub: %s' % (a.which, e)); return 2

    section('SPEC      hand-written expectations')
    s = check(parse, cases.SPEC, a.time_limit, a.verbose, 'spec cases')
    section('REJECT    inputs outside the language must return None')
    r = check(parse, [(g, src, None) for g, src in cases.REJECT], a.time_limit, a.verbose, 'rejections')
    section('FUZZ      %d random arithmetic expressions; expectation from Python\'s own ast' % a.fuzz)
    f = check(parse, [(cases.ARITH, src, want) for src, want in cases.fuzz(a.fuzz)], a.time_limit, a.verbose, 'fuzz cases')
    section('DESIGN    the notation does not settle these; reported, never failed')
    for grammar, src, question, readings in cases.DESIGN:
        got, err = run(parse, grammar, src, a.time_limit)
        match = [k for k, v in readings.items() if err is None and v == got]
        print('  %r\n    %s\n    -> %s%s%s   %s' % (src, question, YELLOW, match[0] if match else 'none of the listed readings', OFF, DIM + (err or show(got)) + OFF))
    section('TIMING    doubling n until %.0fs; exponent fitted on log-log' % a.time_limit)
    t = timing(parse, a.time_limit)
    print()
    return 0 if (s and r and f and t) else 1

if __name__ == '__main__':
    sys.exit(main())

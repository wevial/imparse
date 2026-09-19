# rewrite — two ways to replace the 2014 backtracking parser

The 2014 parser (`../working/imparse.py`) is backtracking recursive descent. Measured here:

- every binary operator nests to the right, so `1 - 2 - 3` is `1 - (2 - 3)`; the `Assoc*` tags are never read;
- precedence layers are not enforced: `1 * 2 + 3` parses as `1 * (2 + 3)`;
- a chain of prefix operators or nested parentheses is exponential: 8 tokens take about a second, 16 time out;
- plain infix chains are roughly quadratic.

Two replacements to try, each a stub with notes on what will bite. `OPTIONS.md` has the reasoning: why these two, what else was considered, and the references.

| | file | idea | expected cost |
|---|---|---|---|
| Pratt | `parser_pratt.py` | Pratt parser whose binding powers are derived from the grammar's layers and `Assoc*` tags, memoized descent for the rest | linear |
| Derivatives | `parser_derivatives.py` | parsing with derivatives: rewrite the grammar once per token, no recursion over the input | cubic worst case, near-linear with compaction |

## Running it

```
python3 harness.py old            # the 2014 parser, as a baseline
python3 harness.py pratt          # parser_pratt.py
python3 harness.py derivatives    # parser_derivatives.py
python3 harness.py pratt -v       # show passing cases too
```

Python 3, standard library only. A parser exposes one function, `parse(grammar, tokens) -> tree | None`; the harness tokenizes with the 2014 tokenizer so you can stay on parsing.

## What it checks

- **SPEC**: hand-written expectations. Associativity, precedence across layers, `-` as both prefix and infix, optional and repeated groups including empty ones.
- **REJECT**: inputs outside the language must return `None`.
- **FUZZ**: 300 random arithmetic expressions. The expected tree comes from Python's own `ast` module, since the `ARITH` grammar was built to agree with Python's expression grammar. It is an oracle neither of us wrote.
- **DESIGN**: four inputs where the notation does not settle the answer. Reported, never failed. Decide, then move them into SPEC.
- **TIMING**: four input families, doubling n until a single parse takes 3 seconds, exponent fitted on a log-log line. Green under n^1.35.

Baseline for `old`: 17 of 21 SPEC, 12 of 12 REJECT, about a third of FUZZ, and no timing family gets past n = 1024.

## Not covered yet

The `>>` `<<` indentation markers from the `.p` notation are not in the Python ADT, so nothing here tests layout. Reading `.p` files directly is also out of scope; grammars are built with the ADT in `grammars.py`.

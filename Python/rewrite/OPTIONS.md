# Options for replacing the parser

Notes from a conversation in September 2026 about an idea from 2014: rewrite imparse's parser so it is not (necessarily) recursive and runs in better time. Recursion was later taken off the list of things to avoid; what matters is the time.

## What is wrong with the current one

`../working/imparse.py` is backtracking recursive descent. It tries each choice in order, and when one fails it starts the next from the same position, re-parsing spans it has already parsed. Measured with `harness.py old`:

- prefix chains and nested parentheses are exponential: 8 tokens take about a second, 16 time out;
- infix chains are about n^1.8;
- every binary operator nests to the right, and the `Assoc*` tags in the ADT are never read;
- precedence layers (the `^` in the `.p` notation) are not enforced, so `1 * 2 + 3` is `1 * (2 + 3)`;
- `e ::= e + e` only works through the `leftFactor` flag, which is a workaround for left recursion.

## The constraint that shapes the choice

imparse interprets the grammar as data at run time, so that one small parser can be ported to Python, JavaScript, PHP and Haskell. That rules out anything that needs a table-generation step (LR, LALR, GLR): the generator would have to be ported too. Whatever replaces the parser should be a few hundred lines of loops, maps and pattern matches over the grammar ADT.

## The two chosen

### Pratt, derived from the grammar — `parser_pratt.py`

Top-down operator precedence (Pratt, 1973). Parse one operand; then, while the next token is an infix operator that binds at least as tightly as the current minimum, consume it and recurse for the right-hand side. It is recursive, but each token is consumed exactly once, so it is linear. Left recursion is not a problem because `e ::= e + e` is never expanded; it becomes an entry in an operator table.

The part that is a little new: almost every Pratt parser is hand-written, with binding powers typed in as numbers. imparse's notation already declares them. Layer position gives the power, the `Assoc*` tag gives the direction, and the shape of a choice says what kind of operator it is:

| shape of the choice | becomes |
|---|---|
| own nonterminal, terminal, own nonterminal | infix operator |
| terminal first, own nonterminal last | prefix operator |
| anything else | atom, parsed by ordinary descent |

So the tables can be derived at load time. tree-sitter and Ohm do related things with explicit precedence annotations; deriving it from a positional notation is the novel-ish bit.

Everything that is not an operator (sequences, optional and repeated groups, other nonterminals) still uses descent. Memoized on (nonterminal, position, minimum power) it stays linear.

- **Cost:** linear.
- **Handles:** precedence, associativity, one token in two roles (`-` as prefix and infix).
- **Does not handle:** ambiguity. Like any deterministic parser it commits to the first thing that fits.
- **Exercises:** loops, tables, one clean recursive function.

### Parsing with derivatives — `parser_derivatives.py`

Brzozowski (1964) defined the derivative of a regular language with respect to a character: the set of things that may follow that character. Might, Darais and Spiewak (2011) extended it to context-free grammars using laziness, memoization and fixed points. Parsing becomes a loop with no recursion over the input:

```
lang = grammar
for tok in tokens:
    lang = derive(lang, tok)
return the trees of `lang` that match the empty string
```

All the work is in rewriting the grammar as a data structure, which is what imparse's ADT and UxADT's pattern matching were built for. A core language of about six node kinds (empty, epsilon, token, alternative, sequence, reduction, plus lazy references) and one `derive` case for each.

Three things make or break it: references must be derived lazily and memoized, or left recursion loops forever; `nullable` and tree extraction are least fixed points over a cyclic graph, not plain recursion; and without compaction the grammar grows with every token and the exponential curve comes back. Adams, Hollenbeck and Might (2016) showed that with compaction it is cubic in the worst case and close to linear in practice.

It returns all parses, so `1 - 2 - 3` yields two trees. The layers and `Assoc*` tags become a filter that discards the wrong ones, which is the principled version of what those annotations were reaching for.

The novel-ish bits: carrying imparse's choice labels through the derivative to build the labelled trees, using layers and associativity as a disambiguation filter inside the derivative, and (later) making the `>>` `<<` layout markers behave under derivation.

- **Cost:** cubic worst case, near-linear when compaction is done well.
- **Handles:** left recursion natively, ambiguity explicitly.
- **Exercises:** laziness, fixed points, structural recursion over a type.

### Side by side

| | Pratt, derived | Derivatives |
|---|---|---|
| Recursive over the input | yes | no |
| Time | linear | cubic worst case, near-linear in practice |
| Left recursion | sidestepped: becomes an operator table | native, given lazy references |
| Ambiguity | cannot see it | returns every parse; filter by layer and associativity |
| Size | small; a weekend | small to state, subtle to get fast |
| Best reason to pick it | it is the practical answer | it is the one closest to what made the original design nice |

## Considered, not chosen

**Earley** (Earley 1970; Leo 1991; Aycock and Horspool 2002). A chart filled left to right by three operations in a loop: predict, scan, complete. No recursion at all, native left recursion, all parses, cubic worst case, quadratic for unambiguous grammars, linear for deterministic ones with Leo's optimization. It interprets the grammar as data, so it ports well. This was the first recommendation when the goal was "not recursive". The textbook algorithm mishandles nullable rules (exactly the optional and repeated groups); Aycock and Horspool give the ten-line fix. Still a good third option, and a useful cross-check for the other two.

**Packrat** (Ford 2002). Keep recursive descent, memoize every (rule, position) pair: linear time, always. The smallest change to the existing code. Two costs: it needs Warth, Douglass and Millstein's (2008) seed-growing trick to support left recursion, and its ordered choice silently hides ambiguity, which means precedence has to be encoded in rule order, fighting the `^` notation instead of using it.

**LR, LALR, GLR.** Linear and well understood, but they need a table generator, which breaks the constraint above.

## Decisions the notation leaves open

`harness.py` reports these under DESIGN and never fails them. Each needs an answer before either parser is finished:

1. How do a repeated group's results join the parent's children: spliced flat, or as a nested list? The 2014 parser does one for a single result and the other for several.
2. Does a prefix operator in a tighter layer stop at its layer? `not 1 == 1 and true`.
3. Two operators in one layer, both `AssocNone`: left, right, or reject as ambiguous? `true and false or true`.
4. Is a prefix operator always allowed in operand position, even when its layer is looser than the operator to its left? `2 ^ - 1`. Python says yes.

## References

- V. Pratt. *Top Down Operator Precedence.* POPL 1973.
- J. Brzozowski. *Derivatives of Regular Expressions.* JACM 11(4), 1964.
- M. Might, D. Darais, D. Spiewak. *Parsing with Derivatives: A Functional Pearl.* ICFP 2011.
- M. Adams, C. Hollenbeck, M. Might. *On the Complexity and Performance of Parsing with Derivatives.* PLDI 2016.
- J. Earley. *An Efficient Context-Free Parsing Algorithm.* CACM 13(2), 1970.
- J. Leo. *A General Context-Free Parsing Algorithm Running in Linear Time on Every LR(k) Grammar Without Using Lookahead.* TCS 82, 1991.
- J. Aycock, R. N. Horspool. *Practical Earley Parsing.* The Computer Journal 45(6), 2002.
- B. Ford. *Packrat Parsing: Simple, Powerful, Lazy, Linear Time.* ICFP 2002.
- A. Warth, J. Douglass, T. Millstein. *Packrat Parsers Can Support Left Recursion.* PEPM 2008.

"""Approach B — parsing with derivatives (Brzozowski 1964; Might, Darais & Spiewak 2011).

The idea: the derivative of a language L with respect to a token c is the set of things that
may FOLLOW c in L. Parsing is then a loop with no recursion over the input at all:

    lang = grammar
    for tok in tokens:  lang = derive(lang, tok)
    return the parse trees of `lang` that match the empty string

All the work is in rewriting the grammar as data, which is what your ADT was built for.
First translate the imparse Grammar into a small core language; six node kinds is enough:

    Empty            matches nothing
    Eps(trees)       matches the empty string, yielding these trees
    Tok(pred)        matches one token
    Alt(a, b)        either
    Seq(a, b)        a then b
    Red(a, f)        a, with f applied to its result   <- this is how labels build {'Plus': [...]}
    Ref(name)        a named nonterminal, resolved lazily

and derive is one case each:

    D(Empty) = D(Eps) = Empty
    D(Tok p)  = Eps([c]) if p(c) else Empty
    D(Alt a b) = Alt(D a, D b)
    D(Seq a b) = Alt(Seq(D a, b),  Seq(Eps(nullparse a), D b))   <- second half only if a is nullable
    D(Red a f) = Red(D a, f)

Things that will bite, in the order you will probably meet them:
  1. Left recursion: D(e) where e ::= e + e asks for D(e) again, forever. The derivative of a
     Ref must be a NEW lazy Ref, memoized on (name, token, identity of the language), created
     before its body is computed. This one idea is the difference between looping and working.
  2. nullable(lang) is a least fixed point over a cyclic graph, not a simple recursion. Start
     everything at False and iterate until nothing changes (or do it Kleene-style with a
     worklist). Same for extracting the final trees.
  3. Without compaction the grammar grows on every token and you get the exponential curve
     back. Simplify as you build:  Seq(Empty, _) = Empty,  Alt(Empty, x) = x,
     Seq(Eps(t), x) = Red(x, prepend t),  Red(Red(x, f), g) = Red(x, g . f).
     Adams, Hollenbeck & Might (2016) show this gets you cubic worst case and near-linear in
     practice. The TIMING section will tell you how close you got.
  4. Derivatives return ALL parses. '1 - 2 - 3' has two. The Assoc* tags and the layer order
     are your filter: either prune in the Red for an infix choice (reject a right child from
     the same layer when AssocLeft, and so on) or rewrite the grammar into a stratified one
     before you start. The first is more fun; the second is ten lines.
  5. May / Many / MayMany desugar to Alt and recursion:  Many x = Seq(x, MayMany x),
     MayMany x = Alt(Eps([]), Many x). Decide early how a group's trees join the parent's children. The 2014 parser splices
     a single result flat and nests several as a list; that is DESIGN case 1, yours to settle.

Interface the harness expects:  parse(grammar, tokens) -> tree | None
Tree format: see the top of cases.py.
"""
import grammars  # noqa: F401  (puts ../working on sys.path)
from imparse import *  # noqa: F401,F403

def parse(grammar, tokens):
    raise NotImplementedError('write me: core language, derive, nullable fixpoint, compaction')

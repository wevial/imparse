"""Pratt — a Pratt parser derived from the grammar, memoized descent for everything else.

The idea: nobody should type binding powers by hand when the grammar already declares them.
At load time, walk each Production and sort its choices:

  * first symbol is the production's own nonterminal, then a terminal, then the nonterminal
        -> an INFIX operator. Its layer index is its binding power; its Assoc* tag decides
           whether the right operand is parsed at the same power (right) or one tighter (left).
  * first symbol is a terminal and the LAST symbol is the production's own nonterminal
        -> a PREFIX operator. (Which power does its operand get? That is DESIGN case 1.)
  * anything else -> an ATOM, parsed by ordinary descent over its sequence.

Then the classic loop: parse one prefix-or-atom, and while the next token is an infix operator
whose power is at least the current minimum, consume it and recurse for the right side.
Every token is consumed once, so this is linear even though it is recursive.

Sequences inside atoms (One / May / Many / MayMany, nested nonterminals) still need descent.
Memoize on (nonterminal, position, min_power) and that stays linear too.

Things that will bite, in the order you will probably meet them:
  1. '-' is both prefix and infix in ARITH. Which table you look in depends on whether you are
     expecting an operand or an operator. That is the whole trick of Pratt; keep two tables.
  2. AssocNone in an infix layer ('1 == 2 == 3'). Reject, or pick a side? Your call.
  3. Empty May/Many groups must succeed without consuming. Return the position unchanged.
  4. A production with no left-recursive choices at all (CALLS) should fall straight through
     to descent with zero Pratt machinery in the way.

Interface the harness expects:  parse(grammar, tokens) -> tree | None
Tree format: see the top of cases.py.  Unpacking the ADT: see how oracle.py and the 2014
parser use  x.match(Production(_, _), lambda nt, cbs: ...).end   and   x < Terminal(_).
"""
import grammars  # noqa: F401  (puts ../working on sys.path)
from imparse import *  # noqa: F401,F403

def parse(grammar, tokens):
    raise NotImplementedError('write me: Pratt tables from the grammar, then the loop')

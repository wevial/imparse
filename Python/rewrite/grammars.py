"""Test grammars, built with the same ADT the 2014 parser uses.

Layer convention (same as example.py): within a Production, each Choices([...]) block is one
precedence layer, and EARLIER blocks bind LOOSER. That is what the `^` in the .p notation means.
The Assoc* tag on a Choice says how a binary operator in that layer nests.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'working'))
from imparse import (Grammar, Production, Choices, Choice, AssocNone, AssocLeft, AssocRight,
                     One, May, Many, MayMany, Nonterminal, RegExpr, Terminal)

NT, T, RX = Nonterminal, Terminal, RegExpr
NUM = RX('/(0|[1-9][0-9]*)/')

# The grammar from working/example.py, unchanged. The 2014 parser handles all of it.
FORMULA = Grammar([
  Production('formula', [
    Choices([Choice('And', AssocNone(), [NT('formula'), T('and'), NT('formula')]),
             Choice('Or',  AssocNone(), [NT('formula'), T('or'),  NT('formula')])]),
    Choices([Choice('Equal', AssocNone(), [NT('number'), T('=='), NT('number')]),
             Choice('True',  AssocNone(), [T('true')]),
             Choice('False', AssocNone(), [T('false')]),
             Choice('Not',   AssocNone(), [T('not'), NT('formula')])])]),
  Production('number', [
    Choices([Choice('Plus',   AssocNone(), [NT('number'), T('+'), NT('number')]),
             Choice('Minus',  AssocNone(), [NT('number'), T('-'), NT('number')]),
             Choice('Number', AssocNone(), [NUM])])])])

# Arithmetic with real precedence and associativity. Layers, loosest first:
#   + -  (left)   * /  (left)   unary -  (prefix)   ^  (right)   atoms
# Chosen to agree with Python's own expression grammar, so Python's `ast` module is an
# independent oracle for it (see cases.py). '^' here is exponent, i.e. Python's '**'.
ARITH = Grammar([
  Production('e', [
    Choices([Choice('Plus',  AssocLeft(),  [NT('e'), T('+'), NT('e')]),
             Choice('Minus', AssocLeft(),  [NT('e'), T('-'), NT('e')])]),
    Choices([Choice('Times', AssocLeft(),  [NT('e'), T('*'), NT('e')]),
             Choice('Div',   AssocLeft(),  [NT('e'), T('/'), NT('e')])]),
    Choices([Choice('Neg',   AssocNone(),  [T('-'), NT('e')])]),
    Choices([Choice('Pow',   AssocRight(), [NT('e'), T('^'), NT('e')])]),
    Choices([Choice('Paren', AssocNone(),  [T('('), NT('e'), T(')')]),
             Choice('Number', AssocNone(), [NUM])])])])

# Optional and repeated groups: the branch the tok() bug lived in, and where nullable rules bite.
#   call ::= id ( [arg {, arg}] )        stmt ::= let id = call [;]
IDENT = RX('/[a-z][a-z0-9]*/')
CALLS = Grammar([
  Production('stmt', [
    Choices([Choice('Let', AssocNone(), [T('let'), IDENT, T('='), NT('call'), May([T(';')])])])]),
  Production('call', [
    Choices([Choice('Call', AssocNone(),
                    [IDENT, T('('), May([NT('arg'), MayMany([T(','), NT('arg')])]), T(')')])])]),
  Production('arg', [
    Choices([Choice('ArgCall', AssocNone(), [NT('call')]),
             Choice('ArgNum',  AssocNone(), [NUM])])])])

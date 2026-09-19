"""What a correct parser returns. Tree format is the 2014 one, so old and new are comparable:
     {'Label': [children]}   a choice with children
     'Label'                 a choice with no children (all terminals)
     '42'                    a regex leaf

Four kinds of case:
  SPEC    hand-written expectation; must pass.
  REJECT  input is not in the language; parser must return None.
  FUZZ    random arithmetic; expectation comes from Python's own `ast`, an independent oracle.
  DESIGN  the grammar notation does not settle the answer. Reported, never failed. Decide,
          then move the case to SPEC.
"""
import ast, random
from grammars import FORMULA, ARITH, CALLS

def N(label, *kids):
    return {label: list(kids)} if kids else label
def num(n):
    return N('Number', str(n))

SPEC = [
  # --- things the 2014 parser already gets right (the harness checks that it agrees) ---
  (FORMULA, 'true', 'True'),
  (FORMULA, 'not true', N('Not', 'True')),
  (FORMULA, 'true and false', N('And', 'True', 'False')),
  (FORMULA, '1 == 2', N('Equal', num(1), num(2))),
  (FORMULA, '1 + 2 == 3', N('Equal', N('Plus', num(1), num(2)), num(3))),
  (ARITH, '7', num(7)),
  (ARITH, '( 7 )', N('Paren', num(7))),
  # --- associativity: the 2014 parser nests everything to the right ---
  (ARITH, '1 - 2 - 3', N('Minus', N('Minus', num(1), num(2)), num(3))),
  (ARITH, '8 / 4 / 2', N('Div', N('Div', num(8), num(4)), num(2))),
  (ARITH, '2 ^ 3 ^ 2', N('Pow', num(2), N('Pow', num(3), num(2)))),
  # --- precedence across layers ---
  (ARITH, '1 + 2 * 3', N('Plus', num(1), N('Times', num(2), num(3)))),
  (ARITH, '1 * 2 + 3', N('Plus', N('Times', num(1), num(2)), num(3))),
  (ARITH, '( 1 + 2 ) * 3', N('Times', N('Paren', N('Plus', num(1), num(2))), num(3))),
  (ARITH, '2 * 3 ^ 2', N('Times', num(2), N('Pow', num(3), num(2)))),
  # --- one token, two roles: '-' as prefix and as infix ---
  (ARITH, '- 1', N('Neg', num(1))),
  (ARITH, '1 - - 2', N('Minus', num(1), N('Neg', num(2)))),
  (ARITH, '- 2 ^ 2', N('Neg', N('Pow', num(2), num(2)))),
  (ARITH, '- 1 - 2', N('Minus', N('Neg', num(1)), num(2))),
  # --- optional and repeated groups, including the empty ones ---
  (CALLS, 'let x = f ( )', N('Let', 'x', N('Call', 'f'))),
  (CALLS, 'let x = f ( ) ;', N('Let', 'x', N('Call', 'f'))),
  (CALLS, 'let x = f ( 1 )', N('Let', 'x', N('Call', 'f', N('ArgNum', '1')))),
]

REJECT = [
  (FORMULA, 'true and'), (FORMULA, 'and true'), (FORMULA, ''), (FORMULA, 'true true'),
  (ARITH, '1 +'), (ARITH, '( 1'), (ARITH, '1 )'), (ARITH, '1 2'), (ARITH, '* 1'),
  (CALLS, 'let x = f ( , )'), (CALLS, 'let x = f ( 1 , )'), (CALLS, 'let = f ( )'),
]

DESIGN = [
  (CALLS, 'let x = f ( 1 , 2 , 3 )',
   "How do a repeated group's results join the parent's children? The 2014 parser is inconsistent: "
   "one result is spliced in flat (see the SPEC case 'f ( 1 )'), several arrive as a nested list.",
   {'spliced flat': N('Let', 'x', N('Call', 'f', N('ArgNum', '1'), N('ArgNum', '2'), N('ArgNum', '3'))),
    'nested list (2014)': N('Let', 'x', {'Call': ['f', [N('ArgNum', '1'), N('ArgNum', '2'), N('ArgNum', '3')]]})}),
  (FORMULA, 'not 1 == 1 and true',
   "Does a prefix operator in a TIGHTER layer stop at its layer? The 2014 parser says no: "
   "Not[And[..]]. Reading the layers as precedence says yes: And[Not[Equal], True].",
   {'layers-as-precedence': N('And', N('Not', N('Equal', num(1), num(1))), 'True'),
    '2014 behaviour':       N('Not', N('And', N('Equal', num(1), num(1)), 'True'))}),
  (FORMULA, 'true and false or true',
   "And and Or share a layer and are AssocNone. Left-nest, right-nest, or reject as ambiguous?",
   {'left':  N('Or', N('And', 'True', 'False'), 'True'),
    'right (2014)': N('And', 'True', N('Or', 'False', 'True')),
    'reject': None}),
  (ARITH, '2 ^ - 1',
   "Neg sits in a LOOSER layer than Pow. Is a prefix operator always allowed in operand "
   "position (Python says yes: 2 ** -1), or do layers forbid it?",
   {'allowed': N('Pow', num(2), N('Neg', num(1))), 'forbidden': None}),
]

# ---- FUZZ: random ARITH expressions, expectation derived from Python's parser ----
_OPS = {ast.Add: 'Plus', ast.Sub: 'Minus', ast.Mult: 'Times', ast.Div: 'Div', ast.Pow: 'Pow'}

def _from_ast(node, parens):
    """Python's ast drops parentheses; `parens` is the set of (lineno, col) where we wrote one."""
    if isinstance(node, ast.Constant):
        t = num(node.value)
    elif isinstance(node, ast.UnaryOp):
        t = N('Neg', _from_ast(node.operand, parens))
    else:
        t = N(_OPS[type(node.op)], _from_ast(node.left, parens), _from_ast(node.right, parens))
    for _ in range(parens.get((node.col_offset, node.end_col_offset), 0)):
        t = N('Paren', t)
    return t

def _gen(rng, depth):
    """Returns python-source text. Never emits a prefix '-' directly after '^' or another '-' ... that is DESIGN territory."""
    if depth == 0 or rng.random() < 0.25:
        return str(rng.randint(0, 99))
    r = rng.random()
    if r < 0.12:
        return '( %s )' % _gen(rng, depth - 1)
    if r < 0.22:
        inner = _gen(rng, depth - 1)
        return '- ' + inner if not inner.startswith('-') else inner
    op = rng.choice(['+', '-', '*', '/', '**'])
    left, right = _gen(rng, depth - 1), _gen(rng, depth - 1)
    if right.startswith('-'):           # keep prefix minus out of right-operand position
        right = '( %s )' % right
    if op == '**' and left.startswith('-'):   # '- a ** b' is fine, but make the intent explicit
        left = '( %s )' % left
    return '%s %s %s' % (left, op, right)

def fuzz(n=300, seed=1964, depth=5):
    rng, out = random.Random(seed), []
    while len(out) < n:
        src = _gen(rng, depth)
        tree = ast.parse(src, mode='eval').body
        # Python's ast drops parentheses, so count how many pairs wrap each node's span.
        # A pair that wraps only another pair (( ( x ) )) is resolved inward to x's span.
        parens, stack, match = {}, [], {}
        for i, ch in enumerate(src):
            if ch == '(':
                stack.append(i)
            elif ch == ')':
                match[stack.pop()] = i
        for j, i in match.items():
            a, b = j + 1, i
            while True:
                while src[a] == ' ': a += 1
                while src[b - 1] == ' ': b -= 1
                if src[a] == '(' and match[a] == b - 1:
                    a, b = a + 1, b - 1
                else:
                    break
            parens[(a, b)] = parens.get((a, b), 0) + 1
        out.append((src.replace('**', '^'), _from_ast(tree, parens)))
    return out

# ---- TIMING: input families that scale, with the token count as n ----
TIMING = [
  ('prefix chain   not not .. true', FORMULA, lambda n: ' '.join(['not'] * (n - 1) + ['true'])),
  ('infix chain    1 + 1 + .. + 1',  ARITH,   lambda n: ' + '.join(['1'] * ((n + 1) // 2))),
  ('nested parens  ( ( .. 1 .. ) )', ARITH,   lambda n: '( ' * (n // 2) + '1' + ' )' * (n // 2)),
  ('mixed          1 + 2 * 3 ^ 4 - ..', ARITH,
     lambda n: ' '.join(t for i in range((n + 1) // 2) for t in (str(i % 9 + 1), '+*^-'[i % 4]))[:-2]),
]

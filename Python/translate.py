#######################################################
##
## Conv.py
##
## A cross-platform parser library.
##
##    Web:     imparse.org
##    Version: 0.0.0.4
##
##
#######################################################

exec(open('imparse.py').read())
exec(open('convGrammar.py').read())

#######################################################
# Reads a .txt file with a grammar conforming to BNF notation
# and transforms to UxADT

def bnfToUxadt(txt):
  txt = open(txt)
  t = txt.read()
  
  r = parser(grammar, t)
  if r is not None:
    pprint.pprint(r)
    r1 = toUxadt(r)
    return r1
  return None


def toUxadt(g):
  # Unwrap
  ps = g['Grammar']
  ps2 = []

  for p in ps:
    prodId = p['Production'][0]
    cs = p['Production'][1:]
    cb = []
    for c in cs:
      (label, seq) = ('', [])
      for i in range(len(c['Choice'])):
        if i == 0:
          label = c['Choice'][i]
        else:
          es = c['Choice'][i]
          r = toUxadtExpr(es)
          if r is not None:
            seq = seq + r
          else: break
      cb = cb + [Choice(label, AssocNone(), seq)]
    ps2 = ps2 + [Production(prodId, [Choices(cb)])]
  return Grammar(ps2)

def toUxadtExpr(es):
  if type(es) == str: 
    return [Terminal(es)]

  cs = []
  ty = list(es.keys())[0]
  x = es[ty][0]

  if ty == 'Terminal':
    cs = cs + [Terminal(x[1:])]
  elif ty == 'Nonterminal':
    cs = cs + [Nonterminal(x[1:])]
  elif ty == 'Empty String':
    cs = cs + [Terminal('\"\"')]
  elif ty == 'RegExpr':
    s = '/' + x[1:-1] + '/'
    cs = cs + [RegExpr(s)]
  # May/Many/MayMany
  elif ty == 'May':
    cs = cs + [May(convExpr(x))]
  elif ty == 'Many':
    cs = cs + [Many(convExpr(x))]
  elif ty == 'MayMany':
    cs = cs + [MayMany(convExpr(x))]
  # Group
  elif ty == 'Group':
    cs = cs + convExpr(x)

  return cs

#######################################
# Writes a UxADT grammar to a file
def writeUxadt(u, r = False):
  s = uxadtToStr(u)
  f = open('eg.py', 'w')
  f.write('g = ')
  f.write(s)
  f.close()
  if r:
    return s

def uxadtToStr(g, pr = False):
  ps = g.match(Grammar(_), lambda ps: ps).end
  st = 'Grammar([\\'
  for p in ps:
    (nt, cbs) = p.match(Production(_, _), lambda nt, cbs: (nt, cbs)).end
    st = st + '\n\tProduction(\'' + nt + '\', [\\'
    for cb in cbs:
      cs = cb.match(Choices(_), lambda cs: cs).end
      st = st + '\n\t\tChoices(['
      for c in cs:
        (label, seq) = c.match(Choice(_, _, _), lambda l, a, seq: (l, seq)).end
        st = st + '\n\t\t\tChoice(\'' + label + '\', AssocNone(), [\\'
        r = uxadtExprToStr(seq)
        st = st + '\n\t\t\t\t' + r + '\\\n\t\t\t\t]),\\'
      st = st + '\n\t\t\t]),\\'
    st = st + '\n\t\t]),\\'
  st = st + '\n\t])'
  if pr:
    print(st)
  return st

def uxadtExprToStr(seq):
  s = ''
  for x in seq:
    et = etype(x)
    if et is not None:
      (ty, expr) = et
    else:
      (ty, seq2) = ptype(x)
 
    if ty == 'One':
      r = uxadtExprToStr(seq2)
      s = s + 'One([' + r + ']), '
    if ty == 'May':
      r = uxadtExprToStr(seq2)
      s = s + 'May([' + r + ']), '
    elif ty == 'Many':
      r = uxadtExprToStr(seq2)
      s = s + 'Many([' + r + ']), '
    elif ty == 'MayMany':
      r = uxadtExprToStr(seq2)
      s = s + 'MayMany([' + r + ']), '
    elif ty == 'Terminal':
      s = s + 'Terminal(\'' + expr + '\'), '
    elif ty == 'RegExpr':
      s = s + 'RegExpr(\'' + expr + '\'), '
    elif ty == 'Nonterminal':
      s = s + 'Nonterminal(\'' + expr + '\'), '
  return s


  

##eof
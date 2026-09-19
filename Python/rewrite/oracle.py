"""The 2014 backtracking parser, wrapped so it is quiet and cannot hang the harness."""
import contextlib, io, signal
import grammars  # noqa: F401  (puts ../working on sys.path)
import imparse as _old

class Timeout(Exception):
    pass

def _alarm(*_):
    raise Timeout()

def tokenize(grammar, s):
    ps = grammar.match(_old.Grammar(_old._), lambda ps: ps).end
    return _old.tokenize(ps, s)

def run_with_timeout(fn, seconds):
    """Returns (result, None) or (None, 'timeout' | 'recursion' | 'error: ...')."""
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn(), None
    except Timeout:
        return None, 'timeout'
    except RecursionError:
        return None, 'recursion'
    except NotImplementedError:
        raise
    except Exception as e:  # a crash in a parser under test is a result, not a harness failure
        return None, 'error: %s: %s' % (type(e).__name__, e)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

def parse(grammar, tokens):
    with contextlib.redirect_stdout(io.StringIO()):
        return _old.parser(grammar, list(tokens))

# A copy of the game with a hook for tests (window.__ev): python3 mkdbg.py index.html DIR -> DIR/ed/dbg.html
import sys, os
os.makedirs(sys.argv[2] + '/ed', exist_ok=True)
s=open(sys.argv[1]).read()
k="menu();\nrequestAnimationFrame(loop);\n"
assert k in s
s=s.replace(k,k+"window.__ev = c => eval(c);\n",1)
open(sys.argv[2] + '/ed/dbg.html','w').write(s)

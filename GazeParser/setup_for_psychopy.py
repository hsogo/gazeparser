import sys
import runpy

if len(sys.argv)==1:
    sys.argv.append('install')
else:
    sys.argv[1]='install'

runpy.run_path("setup.py")

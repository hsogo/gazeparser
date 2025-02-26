import os
import re
import codecs
import argparse

parser = argparse.ArgumentParser(description='Update Copyright year')
parser.add_argument('year', type=int, help='Year')

args = parser.parse_args()

s = re.compile('Copyright \(C\) ([\d-]+)')
checklist = ['LICENSE.txt', 'copyright']

for root, dirs, files in os.walk('.'):
    for file in files:
        b, e = os.path.splitext(file)
        if e.lower() in ['.py', '.cpp', '.hpp'] or file in checklist:
            with codecs.open(os.path.join(root,file), 'r', 'utf-8') as fp:
                out = ''
                found = False
                for line in fp:
                    m = s.search(line)
                    if m is not None:
                        found = True
                        out += re.sub('(\d{4})-(\d{4})', '\\1-'+str(args.year), line)
                    else:
                        out += line
            if found:
                print('Found in: {}'.format(file))
                with codecs.open(os.path.join(root,file), 'w', 'utf-8') as fp:
                    fp.write(out)

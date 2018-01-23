#! /usr/bin/env python3

import unittest
import random
import functools
import os
import sys
from subprocess import Popen, PIPE

class BasicTest(unittest.TestCase):
    def run_prog(self, *args):
        cmd = ['./doi_to_org.py', *args]
        process = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output = process.communicate()
        if process.wait() != 0:
            sys.stderr.write('with command: %s\nstdout: %s\nstderr: %s\n' % (' '.join(args), output[0].decode('utf8'), output[1].decode('utf8')))
            self.assertTrue(False)
        return output[0].decode('utf8')

    def setUp(self):
        self.maxDiff = None
        with open('test_data/output.org', 'r') as f:
            self.expected = ''.join(f.readlines()).strip()

    def test_doi(self):
        with open('test_data/input.doi', 'r') as f:
            doi = ''.join(f.readlines()).strip()
        output = self.run_prog(doi).strip()
        self.assertEqual(output, self.expected)

    def test_bibtex(self):
        output = self.run_prog('test_data/input.bib').strip()
        self.assertEqual(output, self.expected)

    def test_fixpoint(self):
        first_output = self.run_prog('test_data/input.bib')
        splitted = first_output.split('\n')
        bibtex = []
        in_src = False
        for line in splitted:
            if in_src:
                if line.startswith('#+END_SRC'):
                    break
                else:
                    bibtex.append(line)
            else:
                if line.startswith('#+BEGIN_SRC'):
                    in_src = True
        bibtex = '\n'.join(bibtex)
        with open('/tmp/test_doi.bib', 'w') as f:
            f.write(bibtex)
        second_output = self.run_prog('/tmp/test_doi.bib')
        self.assertEqual(first_output, second_output)

if __name__ == "__main__":
    unittest.main()

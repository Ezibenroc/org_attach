#! /usr/bin/env python3

import unittest
import random
import functools
import os
import sys
import yaml
from subprocess import Popen, PIPE
from doi_to_org import *

class BasicTest(unittest.TestCase):
    def run_prog(self, *args):
        cmd = ['./doi_to_org.py', *args]
        process = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output = process.communicate()
        if process.wait() != 0:
            sys.stderr.write('with command: %s\nstdout: %s\nstderr: %s\n' % (' '.join(args), output[0].decode('utf8'), output[1].decode('utf8')))
            self.assertTrue(False)
        with open(self.orgfile) as f:
            return f.read()

    def create_config(self):
        self.orgfile = os.path.join(os.getcwd(), 'foo.org')
        with open(self.orgfile, 'w') as f:
            f.write('')
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump({CONFIG_ORGFILE_KEY : self.orgfile}, f)

    def tearDown(self):
        os.remove(CONFIG_FILE)
        os.remove(self.orgfile)

    def setUp(self):
        self.maxDiff = None
        with open('test_data/output.org', 'r') as f:
            self.expected = ''.join(f.readlines()).strip()
        self.create_config()

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
        with open(self.orgfile, 'w') as f: # clearing the file...
            f.write('')
        second_output = self.run_prog('/tmp/test_doi.bib')
        self.assertEqual(first_output, second_output)

class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.orgfile = os.path.join(os.getcwd(), 'foo.org')
        with open(self.orgfile, 'w') as f:
            f.write('hello world!')

    def tearDown(self):
        os.remove(CONFIG_FILE)
        os.remove(self.orgfile)

    def test_find_file(self):
        with self.assertRaises(FileNotFoundError):
            find_config_file()
        with open(CONFIG_FILE, 'w') as f:
            f.write('hello: world\n')
        expected = os.path.join(os.getcwd(), CONFIG_FILE)
        self.assertEqual(expected, find_config_file())

    def create_config_file(self, config):
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f)

    def test_get_correct_config(self):
        config = {CONFIG_ORGFILE_KEY: self.orgfile}
        self.create_config_file(config)
        real_config = get_config()
        self.assertEqual(config, real_config)

    def test_get_config_wrongfile(self):
        config = {CONFIG_ORGFILE_KEY: self.orgfile + 'some_other_str'}
        self.create_config_file(config)
        with self.assertRaises(ConfigError):
            get_config()

    def test_get_config_wrongkey(self):
        config = {'foo' : self.orgfile}
        self.create_config_file(config)
        with self.assertRaises(ConfigError):
            get_config()


if __name__ == "__main__":
    unittest.main()

#! /usr/bin/env python3

import unittest
import random
import functools
import os
import sys
import yaml
import filecmp
import shutil
from subprocess import Popen, PIPE
from doi_to_org import *

class Util(unittest.TestCase):
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
        self.create_config()

    def generic_test(self, arg, expected_output_file):
        with open(expected_output_file) as f:
            expected_output = f.read().strip()
        output = self.run_prog(arg).strip()
        self.assertEqual(output, expected_output)

class BibEntryTest(unittest.TestCase):
    def test_basic(self):
        with open('test_data/casanova_input.bib') as f:
            bibtex = f.read()
        bib_list = BibEntry.from_bibtex(bibtex)
        self.assertEqual(len(bib_list), 1)
        bib = bib_list[0]
        self.assertEqual(bib.doi, '10.1016/j.jpdc.2014.06.008')
        self.assertEqual(bib.url, 'https://hal.inria.fr/hal-01017319')
        self.assertEqual(bib.pdf, 'https://hal.inria.fr/hal-01017319/file/simgrid3-journal.pdf')
        self.assertEqual(bib.title, 'Versatile, Scalable, and Accurate Simulation of Distributed Applications and Platforms')
        import warnings
        with warnings.catch_warnings(): # calling the method plaintext() from pybtex causes a depreciation warning, but the proposed altednative does not work
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            self.assertEqual(bib.authors, 'Henri Casanova, Arnaud Giersch, Arnaud Legrand, Martin Quinson, Frédéric Suter')

    def test_missing_author(self):
        with open('test_data/casanova_missing_author_input.bib') as f:
            bibtex = f.read()

        bib_list = BibEntry.from_bibtex(bibtex)
        org_entry = OrgEntry("", bib_list[0], attachment = True)

        with self.assertRaises(SystemExit):
           org_entry.orgmode_from_bibentry()

class OrgEntryTest(unittest.TestCase):
    class MockEntry(AbstractOrgEntry):
        @classmethod
        def fabric(self, orgfile, arg):
            pass

        @property
        def tags(self):
            return ['tag1', 'tag2']

        @property
        def todo(self):
            return 'todo'

        @property
        def title(self):
            return 'title'

        @property
        def properties(self):
            return [('property1', 12), ('property2', 'foo')]

        @property
        def sections(self):
            return super().sections + [('mysection', 'bar')]

    def test_noattach(self):
        entry = self.MockEntry('orgfile')
        self.assertEqual(entry.header_str(), '**** todo title\t:tag1:tag2:')
        self.assertEqual(entry.properties_str(), ':PROPERTIES:\n:property1: 12\n:property2: foo\n:END:')
        self.assertEqual(entry.sections_str(), '***** Summary\n***** Notes\n***** Open Questions [/]\n***** mysection\nbar')
        self.assertEqual(entry.orgmode_from_bibentry(), '\n'.join([entry.header_str(), entry.properties_str(),
            entry.sections_str()]))

    def test_attach(self):
        entry = self.MockEntry('orgfile')
        entry.attached_file_name = 'file.pdf'
        entry.attached_file_hash = 'hash'
        self.assertEqual(entry.header_str(), '**** todo title\t:tag1:tag2:ATTACH:')
        self.assertEqual(entry.properties_str(), ':PROPERTIES:\n:property1: 12\n:property2: foo\n:Attachments: file.pdf\n:ID: hash\n:END:')
        self.assertEqual(entry.sections_str(), '***** Summary\n***** Notes\n***** Open Questions [/]\n***** mysection\nbar')
        self.assertEqual(entry.orgmode_from_bibentry(), '\n'.join([entry.header_str(), entry.properties_str(),
            entry.sections_str()]))

class BasicCommandLineTest(Util):
    def test_doi(self):
        self.generic_test('10.1137/0206024', 'test_data/knuth_output.org')

    def test_bibtex(self):
        self.generic_test('test_data/knuth_input.bib', 'test_data/knuth_output.org')

    def test_fixpoint(self):
        first_output = self.run_prog('test_data/knuth_input.bib')
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

class AttachmentTest(Util):
    def tearDown(self):
        shutil.rmtree('data')
        if os.path.isfile(self.orgfile):
            os.remove(self.orgfile)

    def assert_output_equal(self, expected, real):
        seen_id = False
        for expected_line, real_line in zip(expected.split('\n'), real.split('\n')):
            if expected_line.startswith(':ID:'):
                self.assertFalse(seen_id)
                self.assertTrue(real_line.startswith(':ID:'))
                real_id = real_line.split(':ID:')[-1].strip()
                seen_id = True
            else:
                self.assertEqual(expected_line, real_line)
            if seen_id:
                return real_id


    def generic_test(self, args, file_hash, file_name, expected_output_file):
        with open(expected_output_file) as f:
            expected_output = f.read().strip()
        output = self.run_prog('%s' % (','.join(args))).strip()
        real_id = self.assert_output_equal(expected=expected_output, real=output)
        file_path = os.path.join('data', real_id[:2], real_id[2:], file_name)
        self.assertTrue(os.path.isfile(file_path))
        self.assertEqual(Attachment.crypto_hash(file_path), real_id)

    def test_basic_attachment(self): # attaching knuth_input.bib
        self.generic_test(args=['test_data/knuth_input.bib', 'test_data/knuth_input.bib'],
                file_hash = '37f3616032c0bd00516ce65ff1c0c01ed25f99e5573731d660a4b38539b02346bcf794024c8d4c21e0bed97f50a309c40172ba342870e1526b370a03c55dbf49',
                file_name = 'Fast_Pattern_Matching_in_Strings.txt',
                expected_output_file='test_data/knuth_output_attachment.org')

    def test_url(self):
        self.generic_test(args=['https://hal.inria.fr/hal-01017319v2/bibtex'],
                file_hash = '095c324c84cc92722b52a2e87b63c638d052ea30397646bc4462ee84bca46412c574f89d636d1841d54eae2df7d33a545e97e204ed0147a84c1d89b7deb8081e',
                file_name = 'Versatile,_Scalable,_and_Accurate_Simulation_of_Distributed_Applications_and_Platforms.pdf',
                expected_output_file = 'test_data/casanova_output.org')

    def test_hal(self):
        self.generic_test(args=['hal-01017319v2'],
                file_hash = '095c324c84cc92722b52a2e87b63c638d052ea30397646bc4462ee84bca46412c574f89d636d1841d54eae2df7d33a545e97e204ed0147a84c1d89b7deb8081e',
                file_name = 'Versatile,_Scalable,_and_Accurate_Simulation_of_Distributed_Applications_and_Platforms.pdf',
                expected_output_file = 'test_data/casanova_output.org')

    def test_pdfpath(self):
        with open('test_data/casanova_local_pdf_input.bib') as f:
            bibtex = f.read()

        pdfpath = 'test_data/pdf'
        orgfile = os.path.join(os.getcwd(), 'bar.org')

        bib_list = BibEntry.from_bibtex(bibtex)
        org_entry = OrgEntry(orgfile, bib_list[0], Attachment.from_key(pdfpath, bib_list[0].key))

        org_entry.add_entry()
        self.assertTrue(os.path.isfile("./data/2a" +
            "/b880f480c6e2ef27a84f8e0fd36252ff444f970fe9dec88da2f77c744b85bd" +
            "e4b5cfcf5fdea3286298945facd819af9a07e594f4850410ce7e909ac9c31e84/" +
            "Versatile,_Scalable,_and_Accurate_Simulation_of_Distributed_" +
            "Applications_and_Platforms.pdf"))

        os.remove(orgfile)

    def test_missing_file_pdfpath(self):
        with open('test_data/knuth_input.bib') as f:
            bibtex = f.read()

        os.mkdir('data')

        pdfpath = 'test_data'
        orgfile = os.path.join(os.getcwd(), 'bar.org')

        bib_list = BibEntry.from_bibtex(bibtex)

        with self.assertRaises(FileNotFoundError):
            attachment = Attachment.from_key(pdfpath, bib_list[0].key)

            org_entry = OrgEntry(orgfile, bib_list[0], attachment)
            org_entry.add_entry()

if __name__ == "__main__":
    unittest.main()

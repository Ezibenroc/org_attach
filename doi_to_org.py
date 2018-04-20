#!/usr/bin/env python3

import sys
import requests
import re
import os
import yaml
import hashlib
import shutil
from abc import ABC, abstractmethod
import tempfile
import mimetypes
import magic            # https://pypi.python.org/pypi/python-magic/
import pybtex.database  # https://pypi.python.org/pypi/pybtex/
from pybtex.database.output.bibtex import Writer

CONFIG_FILE = '.doirc'
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'doi2org')
CONFIG_ORGFILE_KEY = 'orgfile'
CONFIG_PDFPATH_KEY = 'pdfpath'

def _find_config_file(dirname):
    filepath = os.path.join(dirname, CONFIG_FILE)
    if os.path.isfile(filepath):
        return filepath
    newpath = os.path.dirname(dirname)
    if newpath == dirname: # root directory
        filename = os.path.join(CONFIG_DIR, CONFIG_FILE)
        if os.path.isfile(filename):
            return filename
        raise FileNotFoundError('No %s file.' % CONFIG_FILE)
    return _find_config_file(newpath)

def find_config_file():
    return _find_config_file(os.getcwd())

class ConfigError(Exception):
    pass

def get_config():
    config_file = find_config_file()
    with open(config_file, 'r') as f:
        config = yaml.load(f)
    if CONFIG_ORGFILE_KEY not in config:
        raise ConfigError('No %s defined in the configuration file.' % CONFIG_ORGFILE_KEY)
    orgfile = config[CONFIG_ORGFILE_KEY]
    if not os.path.isfile(orgfile):
        raise ConfigError('%s %s does not exist.' % (CONFIG_ORGFILE_KEY, orgfile))
    return config

class BibEntry:
    def __init__(self, pybtex_bib):
        self.bib = pybtex_bib
        assert len(self.bib.entries) == 1

    @classmethod
    def bibtex_from_url(cls, url, head=None):
        try:
            req = requests.get(url, headers=head)
        except requests.exceptions.MissingSchema:
            raise BibError('Wrong URL and/or header.')
        if req.status_code != 200:
            raise BibError('Wrong URL and/or header.')
        return req.text

    # Note: to get a JSON instead of a bibtex entry, use head = {'Accept': 'application/vnd.citationstyles.csl+json'}
    @classmethod
    def bibtex_from_doi(cls, doi):
        url = 'http://dx.doi.org/%s' % doi
        head = {'Accept': 'application/x-bibtex'}
        return cls.bibtex_from_url(url, head)

    @classmethod
    def bibtex_from_halid(cls, hal):
        url = 'https://hal.archives-ouvertes.fr/%s/bibtex' % hal
        return cls.bibtex_from_url(url)

    @classmethod
    def bibtex_from_file(cls, filename):
        try:
            with open(filename) as f:
                return f.read()
        except FileNotFoundError:
            raise BibError('Unknown file: %s' % filename)

    @classmethod
    def bibtex_from_arg(cls, arg):
        functions = [
                cls.bibtex_from_file,
                cls.bibtex_from_doi,
                cls.bibtex_from_url,
                cls.bibtex_from_halid,
        ]
        for func in functions:
            try:
                return func(arg)
            except BibError:
                continue
        raise BibError('Argument %s is not an understandable format (not a DOI, not a path to a bibtex file, etc.).')

    @classmethod
    def from_bibtex(cls, bibtex):
        bib = pybtex.database.parse_string(bibtex, bib_format='bibtex')
        if len(bib.entries) == 0:
            raise BibError('Wrong bibtex, no entries.')
        entries = []
        for key, value in bib.entries.items():
            entries.append(pybtex.database.BibliographyData({key : value}))
        return [cls(e) for e in entries]

    @classmethod
    def from_arg(cls, arg):
        bibtex = cls.bibtex_from_arg(arg)
        return cls.from_bibtex(bibtex)

    @property
    def title(self):
        return str(self.bib.entries.values()[0].rich_fields['title'])

    @property
    def doi(self):
        try:
            return str(self.bib.entries.values()[0].fields['doi'])
        except KeyError:
            return ''

    @property
    def bibtex(self):
        return CustomWriter().to_string(self.bib)

    @property
    def url(self):
        try:
            return str(self.bib.entries.values()[0].fields['url'])
        except KeyError:
            return ''

    @property
    def pdf(self):
        return str(self.bib.entries.values()[0].fields['pdf'])

    @property
    def key(self):
        return str(self.bib.entries.keys()[0])

    @property
    def authors(self):
        def format_name(name):
            return name.plaintext()

        def format_person(person):
            names = person.rich_first_names + person.rich_middle_names + person.rich_last_names
            return ' '.join([format_name(name) for name in names])

        try:
            authors = self.bib.entries.values()[0].persons['author']
        except KeyError:
            raise MissingAuthorError("Stopping at bibtex entry '%s' because it had no 'author' field." % (self.bib.entries.keys()[0]))

        names = []
        for person in authors:
            names.append(format_person(person))
        return ', '.join(names)

class CustomWriter(Writer):
    '''
    We disable the Latex encoding done by pybtex. Otherwise, it will add a backslash in front of a lot of things
    in the bibtex.
    For instance, for the url https://doi.org/10.1137%2F0206024, it used to replace '%' by '\%'. Calling the
    program again with the resulting bibtex would then replace the '\%' by a '\\%'. This is obviously buggy,
    so let's just disable it.
    '''
    def _encode(self, text):
        return text


class BibError(Exception):
    pass

class FileError(Exception):
    pass

class MissingAuthorError(KeyError):
    '''Raise when a bibtex entry is missing the "author" field'''
    def __init__(self, message, *args):
        self.message = message
        super(MissingAuthorError, self).__init__(message, *args)

class Attachment:
    def __init__(self, temporary_file):
        self.file = temporary_file

    @classmethod
    def tempfile_from_url(cls, url):
        try:
            req = requests.get(url)
        except requests.exceptions.MissingSchema:
            raise FileError('Wrong URL.')
        if req.status_code != 200:
            raise FileError('Wrong URL.')
        f = tempfile.NamedTemporaryFile()
        f.file.write(req.content)
        return f

    @classmethod
    def tempfile_from_path(cls, path):
        if not os.path.isfile(path):
            raise FileError('Not a valid path.')
        f = tempfile.NamedTemporaryFile()
        shutil.copyfile(path, f.name)
        return f

    @classmethod
    def tempfile_from_key(cls, path, key):
        if not os.path.isdir(path):
            raise FileError('Not a valid path.')

        for root, dirs, files in os.walk(path):
            for f in files:
                if os.path.splitext(f)[0] == key:
                    temp_f = tempfile.NamedTemporaryFile()
                    shutil.copyfile(os.path.join(root, f), temp_f.name)
                    return temp_f

        raise FileNotFoundError("Couldn't find file '%s' in '%s'" % (key, path))

    @classmethod
    def tempfile_from_arg(cls, arg):
        functions = [
                cls.tempfile_from_path,
                cls.tempfile_from_url,
        ]
        for func in functions:
            try:
                return func(arg)
            except FileError:
                continue
        raise FileError('Argument %s is not an understandable format (not a DOI, not a path to a bibtex file, etc.).')

    @classmethod
    def from_arg(cls, arg):
        return cls(cls.tempfile_from_arg(arg))

    @classmethod
    def from_key(cls, path, key):
        return cls(cls.tempfile_from_key(path, key))

    @property
    def path(self):
        return self.file.name

    @classmethod
    def crypto_hash(cls, filename):
    # https://stackoverflow.com/a/3431838/4110059
        h = hashlib.sha512()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

    @property
    def hash(self):
        return self.crypto_hash(self.file.name)

    @property
    def extension(self):
        mime = magic.from_file(self.path, mime=True)
        if mime == 'text/plain':
            return '.txt' # mimetypes return some weird things for plain text
        return mimetypes.guess_extension(mime)

    def move_to(self, target):
        shutil.move(self.path, target)
        try:
            self.file.close() # avoid the exception when the object eventually get deleted
        except FileNotFoundError:
            pass

class AbstractOrgEntry(ABC):
    star_level = 4

    def __init__(self, orgfile, attachment=None):
        self.orgfile = orgfile
        self.attachment = attachment
        self.attached_file_name = None
        self.attached_file_hash = None

    def attach_file(self, file_name, file_hash):
        org_dir = os.path.dirname(self.orgfile)
        data_dir = os.path.join(org_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        first_level_dir = os.path.join(data_dir, file_hash[:2])
        os.makedirs(first_level_dir, exist_ok=True)
        last_level_dir = os.path.join(first_level_dir, file_hash[2:])
        os.makedirs(last_level_dir) # if it already existed, this is a problem we want to know
        self.attachment.move_to(os.path.join(last_level_dir, file_name))

    @property
    @abstractmethod
    def tags(self):
        pass

    @property
    @abstractmethod
    def todo(self):
        pass

    @property
    @abstractmethod
    def title(self):
        pass

    def header_str(self):
        tags = self.tags
        if self.attached_file_name:
            tags.append('ATTACH')
        tags = ':%s:' % ':'.join(tags)
        header = ['*'*self.star_level, self.todo, self.title]
        h= ' '.join(header) + '\t' + tags
        return h

    @property
    @abstractmethod
    def properties(self):
        pass

    def properties_str(self):
        properties = []
        all_prop = self.properties
        if self.attached_file_name:
            all_prop.append(('Attachments', self.attached_file_name))
            all_prop.append(('ID',         self.attached_file_hash))
        all_prop = [('PROPERTIES', None)] + all_prop + [('END', None)]
        for prop_name, prop_val in all_prop:
            prop = ':%s:' % prop_name
            if prop_val:
                prop = ' '.join([prop, str(prop_val)])
            properties.append(prop)
        return '\n'.join(properties)

    @property
    def sections(self):
        return [('Summary', None), ('Notes', None), ('Open Questions [/]', None)]

    def sections_str(self):
        sections = []
        for sect_name, sect_val in self.sections:
            sect = ' '.join(['*'*(self.star_level+1), sect_name])
            if sect_val:
                sect = '\n'.join([sect, str(sect_val)])
            sections.append(sect)
        return '\n'.join(sections)

    def orgmode_from_bibentry(self):
        header     = self.header_str()
        properties = self.properties_str()
        sections   = self.sections_str()
        return '\n'.join([header, properties, sections])

class OrgEntry(AbstractOrgEntry):
    def __init__(self, orgfile, bibentry, attachment=None):
        super().__init__(orgfile, attachment)
        self.bibentry = bibentry
        if not self.attachment: # no attachment specified, trying to grab it
            try:
                self.attachment = Attachment.from_arg(self.bibentry.pdf)
            except (FileError, KeyError): # bad luck, could not grab it, let's not attach anything
                pass

    @property
    def tags(self):
        return ['PAPER']

    @property
    def todo(self):
        return 'UNREAD'

    @property
    def title(self):
        return self.bibentry.title

    @property
    def properties(self):
        try:
            return [('DOI', self.bibentry.doi),
                    ('URL', self.bibentry.url),
                    ('AUTHORS', self.bibentry.authors),
                   ]
        except MissingAuthorError as e:
            sys.exit(e)

    @property
    def sections(self):
        bib = '#+BEGIN_SRC bib :tangle bibliography.bib\n%s#+END_SRC' % self.bibentry.bibtex
        return super().sections + [('BibTeX', bib)]

    def generate_attachment_file_name(self):
        return self.bibentry.title.replace(' ', '_') + self.attachment.extension

    def add_entry(self):
        if self.attachment:
            self.attached_file_name = self.generate_attachment_file_name()
            self.attached_file_hash = self.attachment.hash
        org_txt = self.orgmode_from_bibentry()
        if self.attachment:
            self.attach_file(self.attached_file_name, self.attached_file_hash)
        with open(self.orgfile, 'a') as f:
            f.write(org_txt)
            f.write('\n')

def org_entry_fabric(orgfile, pdfpath, arg):
    arg_list = arg.split(',')
    bib_entries = BibEntry.from_arg(arg_list[0])
    if len(arg_list) == 1:
        if pdfpath:
            return [OrgEntry(orgfile, bib_entry, Attachment.from_key(pdfpath, bib_entry.key)) for bib_entry in bib_entries]
        else:
            return [OrgEntry(orgfile, bib_entry) for bib_entry in bib_entries]
    elif len(arg_list) == 2:
        if len(bib_entries) > 1:
            raise SyntaxError('Argument %s holds several bibliographical entries, but one attachment %s was given.' % (arg_list[0], arg_list[1]))
        bib_entry = bib_entries[0]
        return [OrgEntry(orgfile, bib_entry, Attachment.from_arg(arg_list[1]))]
    else:
        raise SyntaxError('Wrong argument format, got %s.' % arg)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Syntax: %s <doi>\n')
    try:
        config = get_config()
    except FileNotFoundError:
        sys.exit('No configuration file found. Please add a %s file somewhere.' % CONFIG_FILE)
    except ConfigError as e:
        sys.exit('Error with the configuration file: %s' % e)
    orgfile = config[CONFIG_ORGFILE_KEY]
    pdfpath = None
    if CONFIG_PDFPATH_KEY in config:
        pdfpath = config[CONFIG_PDFPATH_KEY]
    for arg in sys.argv[1:]:
        try:
            for entry in org_entry_fabric(orgfile, pdfpath, arg):
                entry.add_entry()
        except FileNotFoundError as e:
            sys.exit(e)


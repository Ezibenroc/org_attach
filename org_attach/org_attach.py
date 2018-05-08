import sys
import requests
import re
import os
import yaml
import json
import hashlib
import shutil
import argparse
from enum import Enum
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from posixpath import basename, dirname
import pathlib
import tempfile
import mimetypes
import magic            # https://pypi.python.org/pypi/python-magic/
import pybtex.database  # https://pypi.python.org/pypi/pybtex/
from pybtex.database.output.bibtex import Writer
from .version import __version__
import nbformat, nbconvert

CONFIG_FILE = '.orgattachrc'
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'orgattach')
CONFIG_ORGFILE_KEY = 'orgfile'
CONFIG_PDFPATH_KEY = 'pdfpath'
CONFIG_TAG_KEY = 'tags'
CONFIG_TODO_KEY = 'todo'
CONFIG_PROPERTIES_KEY = 'properties'
CONFIG_SECTIONS_KEY = 'sections'
CONFIG_LEVEL_KEY = 'level'
CONFIG_COMPILATION_KEY = 'compile'

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

def safeget(dct, *keys):
    '''Taken from https://stackoverflow.com/a/25833661/4110059'''
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return None
    return dct

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

class TempFile:
    def __init__(self, filename):
        self.filename = filename
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = pathlib.Path(self.temp_dir.name) / filename

    def write(self, content):
        self.temp_file.write_bytes(content)

    @property
    def name(self):
        return str(self.temp_file)

    def close(self):
        self.temp_dir.cleanup()

class Attachment:
    origin_enum = Enum('Origin', ['key', 'url', 'path'])
    def __init__(self, temporary_file, arg, origin):
        self.file = temporary_file
        self.arg = arg
        self.origin = origin

    @classmethod
    def from_url(cls, url):
        origin = cls.origin_enum.url
        try:
            req = requests.get(url)
        except requests.exceptions.MissingSchema:
            raise FileError('Wrong URL.')
        if req.status_code != 200:
            raise FileError('Wrong URL.')
        f = TempFile(cls.fullname_from_arg(url, origin))
        f.write(req.content)
        return cls(f, url, origin)

    @classmethod
    def from_path(cls, path):
        origin = cls.origin_enum.path
        if not os.path.isfile(path):
            raise FileError('Not a valid path.')
        f = TempFile(cls.fullname_from_arg(path, origin))
        shutil.copyfile(path, f.name)
        return cls(f, path, origin)

    @classmethod
    def from_key(cls, path, key):
        origin = cls.origin_enum.key
        if not os.path.isdir(path):
            raise FileError('Not a valid path.')

        for root, dirs, files in os.walk(path):
            for f in files:
                if os.path.splitext(f)[0] == key:
                    temp_f = TempFile(cls.fullname_from_arg(key, origin))
                    shutil.copyfile(os.path.join(root, f), temp_f.name)
                    attachment = cls(temp_f, key, origin)
                    return attachment
        raise FileNotFoundError("Couldn't find file '%s' in '%s'" % (key, path))

    @classmethod
    def from_arg(cls, arg):
        functions = [
                cls.from_path,
                cls.from_url,
        ]
        for func in functions:
            try:
                return func(arg)
            except FileError:
                continue
        raise FileError('Argument %s is not an understandable format (not a DOI, not a path to a bibtex file, etc.).' % arg)

    @property
    def path(self):
        return self.file.name

    @classmethod
    def fullname_from_arg(cls, arg, origin):
        if origin == cls.origin_enum.key:
            return arg
        elif origin == cls.origin_enum.url:
            return basename(urlparse(arg).path)
        elif origin == cls.origin_enum.path:
            return os.path.basename(arg)
        else:
            assert False

    @property
    def original_fullname(self):
        return self.fullname_from_arg(self.arg, self.origin)

    @property
    def original_name(self):
        return os.path.splitext(self.original_fullname)[0]

    @property
    def original_extension(self):
        return os.path.splitext(self.original_fullname)[1]

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
        ext = self.original_extension
        if ext:
            return ext
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
    type_key = None
    default_config = {}

    def __init__(self, config, attachment=None):
        self.attachment = attachment
        self.orgfile = config[CONFIG_ORGFILE_KEY]
        self.star_level = config[CONFIG_LEVEL_KEY]
        self.config = config.get(self.type_key, self.default_config)

    @classmethod
    @abstractmethod
    def fabric(cls, config, arg):
        pass

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
    def tags(self):
        tags = self.config.get(CONFIG_TAG_KEY, [])
        if isinstance(tags, str): # 0 or 1 tag
            tags = [tags]
        return tags

    @property
    def todo(self):
        return self.config.get(CONFIG_TODO_KEY, None)

    @property
    @abstractmethod
    def title(self):
        pass

    def header_str(self):
        tags = self.tags
        if self.attachment:
            tags.append('ATTACH')
        tags = ':%s:' % ':'.join(tags)
        todo = [self.todo] if self.todo else []
        header = ['*'*self.star_level, *todo, self.title]
        h= ' '.join(header) + '\t' + tags
        return h

    @property
    @abstractmethod
    def properties(self):
        pass

    def properties_str(self):
        properties = []
        all_prop = self.properties
        if self.attachment:
            all_prop.append(('Attachments', self.attachment_file_name))
            all_prop.append(('ID',         self.attachment.hash))
        all_prop = [('PROPERTIES', None)] + all_prop + [('END', None)]
        for prop_name, prop_val in all_prop:
            prop = ':%s:' % prop_name
            if prop_val:
                prop = ' '.join([prop, str(prop_val)])
            properties.append(prop)
        return '\n'.join(properties)

    @property
    def sections(self):
        sect_config = self.config.get(CONFIG_SECTIONS_KEY, [])
        sections = []
        for sect in sect_config:
            sections.append((sect, None))
        return sections

    def sections_str(self):
        sections = []
        for sect_name, sect_val in self.sections:
            sect = ' '.join(['*'*(self.star_level+1), sect_name])
            if sect_val:
                sect = '\n'.join([sect, str(sect_val)])
            sections.append(sect)
        return '\n'.join(sections)

    def to_orgmode(self):
        header     = self.header_str()
        properties = self.properties_str()
        sections   = self.sections_str()
        return '\n'.join([header, properties, sections])

    @property
    @abstractmethod
    def attachment_file_name(self):
        pass

    def add_entry(self):
        org_txt = self.to_orgmode()
        if self.attachment:
            self.attach_file(self.attachment_file_name, self.attachment.hash)
        with open(self.orgfile, 'a') as f:
            f.write(org_txt)
            f.write('\n')

class BibOrgEntry(AbstractOrgEntry):
    type_key = 'bib'
    def __init__(self, config, bibentry, attachment=None):
        super().__init__(config, attachment)
        self.bibentry = bibentry
        if not self.attachment: # no attachment specified, trying to grab it
            try:
                self.attachment = Attachment.from_arg(self.bibentry.pdf)
            except (FileError, KeyError): # bad luck, could not grab it, let's not attach anything
                pass

    @classmethod
    def fabric(cls, config, arg):
        pdfpath = safeget(config, cls.type_key, CONFIG_PDFPATH_KEY)
        arg_list = arg.split(',')
        bib_entries = BibEntry.from_arg(arg_list[0])
        if len(arg_list) == 1:
            if pdfpath:
                return [cls(config, bib_entry, Attachment.from_key(pdfpath, bib_entry.key)) for bib_entry in bib_entries]
            else:
                return [cls(config, bib_entry) for bib_entry in bib_entries]
        elif len(arg_list) == 2:
            if len(bib_entries) > 1:
                raise SyntaxError('Argument %s holds several bibliographical entries, but one attachment %s was given.' % (arg_list[0], arg_list[1]))
            bib_entry = bib_entries[0]
            return [cls(config, bib_entry, Attachment.from_arg(arg_list[1]))]
        else:
            raise SyntaxError('Wrong argument format, got %s.' % arg)

    @property
    def title(self):
        return self.bibentry.title

    @property
    def properties(self):
        try:
            prop = {'DOI' : self.bibentry.doi,
                    'URL' : self.bibentry.url,
                    'AUTHORS' : self.bibentry.authors
                    }
        except MissingAuthorError as e:
            sys.exit(e)
        properties = []
        for p in self.config.get(CONFIG_PROPERTIES_KEY, []):
            properties.append((p, prop[p]))
        return properties

    @property
    def sections(self):
        bib = '#+BEGIN_SRC bib :tangle bibliography.bib\n%s#+END_SRC' % self.bibentry.bibtex
        return super().sections + [('BibTeX', bib)]

    @property
    def attachment_file_name(self):
        return self.bibentry.title.replace(' ', '_') + self.attachment.extension

class IpynbOrgEntry(AbstractOrgEntry):
    type_key = 'ipynb'
    def __init__(self, config, attachment):
        super().__init__(config, attachment)
        with open(self.attachment.path) as f:
            self.metadata = json.load(f)['metadata']
        if self.config.get(CONFIG_COMPILATION_KEY, False):
            self.compile_attachment()

    def compile_attachment(self):
        in_file = self.attachment.path
        with open(in_file) as f_notebook:
            notebook = nbformat.read(f_notebook, as_version=4)
        exporter = nbconvert.HTMLExporter()
        body, _ = exporter.from_notebook_node(notebook)
        out_file = TempFile(self.attachment.original_name + '.html')
        with open(out_file.name, 'w') as f_export:
            f_export.write(body)
        self.attachment = Attachment.from_arg(out_file.name)

    @property
    def tags(self):
        return super().tags + [self.metadata['language_info']['name'].upper()]

    @classmethod
    def fabric(cls, config, arg):
        return [cls(config, Attachment.from_arg(arg))]

    @property
    def title(self):
        name = self.attachment.original_name
        name = name.replace('_', ' ')
        name = '%s%s' % (name[0].upper(), name[1:])
        return name

    @property
    def properties(self):
        prop = {'LANGUAGE' : self.metadata['language_info']['name'],
                'VERSION'  : self.metadata['language_info']['version'],
                }
        properties = []
        for p in self.config.get(CONFIG_PROPERTIES_KEY, []):
            properties.append((p, prop[p]))
        return properties

    @property
    def attachment_file_name(self):
        return self.attachment.original_fullname


CONFIG_TYPES = [BibOrgEntry, IpynbOrgEntry]
TYPE_TO_CLS = {conf.type_key : conf for conf in CONFIG_TYPES}
def main():
    parser = argparse.ArgumentParser(
            description='Automatic templates for org-mode')
    parser.add_argument('--version', action='version',
                    version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument('type', type=str, choices=[config.type_key for config in CONFIG_TYPES],
            help='Type of the file to add.')
    parser.add_argument('entries', type=str, nargs='+',
            help='Descriptors for the entries to add.')
    args = parser.parse_args()
    try:
        config = get_config()
    except FileNotFoundError:
        sys.exit('No configuration file found. Please add a %s file somewhere.' % CONFIG_FILE)
    except ConfigError as e:
        sys.exit('Error with the configuration file: %s' % e)
    cls = TYPE_TO_CLS[args.type]
    for arg in args.entries:
        try:
            for entry in cls.fabric(config, arg):
                entry.add_entry()
        except FileNotFoundError as e:
            sys.exit(e)

if __name__ == '__main__':
    main()

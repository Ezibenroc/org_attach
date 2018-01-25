#!/usr/bin/env python3

import sys
import requests
import re
import os
import yaml
import hashlib
import shutil
import tempfile
import pybtex.database  # https://pypi.python.org/pypi/pybtex/
from pybtex.database.output.bibtex import Writer

CONFIG_FILE = '.doirc'
CONFIG_ORGFILE_KEY = 'orgfile'

def _find_config_file(dirname):
    filepath = os.path.join(dirname, CONFIG_FILE)
    if os.path.isfile(filepath):
        return filepath
    newpath = os.path.dirname(dirname)
    if newpath == dirname: # root directory
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

def bibtex_from_url(url, head=None):
    try:
        req = requests.get(url, headers=head)
    except requests.exceptions.MissingSchema:
        raise BibError('Wrong URL and/or header.')
    if req.status_code != 200:
        raise BibError('Wrong URL and/or header.')
    return req.text

# Note: to get a JSON instead of a bibtex entry, use head = {'Accept': 'application/vnd.citationstyles.csl+json'}
def bibtex_from_doi(doi):
    url = 'http://dx.doi.org/%s' % doi
    head = {'Accept': 'application/x-bibtex'}
    return bibtex_from_url(url, head)

def bibtex_from_halid(hal):
    url = 'https://hal.archives-ouvertes.fr/%s/bibtex' % hal
    return bibtex_from_url(url)

def bibtex_from_file(filename):
    try:
        with open(filename) as f:
            return f.read()
    except FileNotFoundError:
        raise BibError('Unknown file: %s' % filename)

class BibError(Exception):
    pass

def bib_from_bibtex(bibtex):
    bib = pybtex.database.parse_string(bibtex, bib_format='bibtex')
    if len(bib.entries) == 0:
        raise BibError('Wrong bibtex, no entries.')
    return bib

def split_bib(bib):
    entries = []
    for key, value in bib.entries.items():
        entries.append(pybtex.database.BibliographyData({key : value}))
    return entries

def generic_get_bibtex(arg):
    functions = [
            bibtex_from_file,
            bibtex_from_doi,
            bibtex_from_url,
            bibtex_from_halid,
    ]
    for func in functions:
        try:
            return func(arg)
        except BibError:
            continue
    raise BibError('Argument %s is not an understandable format (not a DOI, not a path to a bibtex file, etc.).')

def generic_get_bib(arg):
    return bib_from_bibtex(generic_get_bibtex(arg))

class FileError(Exception):
    pass

def file_from_url(url):
    try:
        req = requests.get(url)
    except requests.exceptions.MissingSchema:
        raise FileError('Wrong URL.')
    if req.status_code != 200:
        raise FileError('Wrong URL.')
    f = tempfile.NamedTemporaryFile()
    f.file.write(req.content)
    return f.name,f

def generic_get_file(arg):
    if os.path.isfile(arg):
        return arg,None
    try:
        return file_from_url(arg)
    except FileError:
        raise FileError('Argument %s is not an understandable format (not a path or a URL to a file, etc.).')

def process_args(args, attach=False):
    entries = []
    for arg in args:
        if attach:
            arg, file_arg = arg.split(',')
        new_entries = split_bib(generic_get_bib(arg))
        if attach:
            if len(new_entries) != 1:
                sys.exit('Error: several bib entries found for %s, but only one attachment' % args)
            else:
                file_tuple = generic_get_file(file_arg)
                entries.append((new_entries[0], file_tuple))
        else:
            entries.extend([(e, None) for e in new_entries])
    return entries

def get_entry(bib): # suppose one and only one entry
    return bib.entries.values()[0]

def get_title(bib):
    return str(get_entry(bib).rich_fields['title'])

def get_doi(bib):
    try:
        return get_entry(bib).fields['doi']
    except KeyError:
        return ''

def get_bibtex(bib):
    return CustomWriter().to_string(bib)

def get_url(bib):
    try:
        return get_entry(bib).fields['url']
    except KeyError:
        return ''

def format_name(name):
    return name.plaintext()

def format_person(person):
    names = person.rich_first_names + person.rich_middle_names + person.rich_last_names
    return ' '.join([format_name(name) for name in names])

def get_authors(bib):
    authors = get_entry(bib).persons['author']
    names = []
    for person in authors:
        names.append(format_person(person))
    return ', '.join(names)

def crypto_hash(filename):
# https://stackoverflow.com/a/3431838/4110059
    h = hashlib.sha512()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

trailing_white_spaces_reg = re.compile('\s*\n') # to remove the whitespaces at the end of the lines

def attach_file(attached_file, org_file, file_name):
    file_hash = crypto_hash(attached_file)
    org_dir = os.path.dirname(org_file)
    data_dir = os.path.join(org_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    first_level_dir = os.path.join(data_dir, file_hash[:2])
    os.makedirs(first_level_dir, exist_ok=True)
    last_level_dir = os.path.join(first_level_dir, file_hash[2:])
    os.makedirs(last_level_dir) # if it already existed, this is a problem we want to know
    shutil.copyfile(attached_file, os.path.join(last_level_dir, file_name))
    return file_hash

def orgmode_from_bibentry(bib, attached_file_name=None, attached_file_hash=None):
    header = '**** UNREAD {title}\t:PAPER:'
    properties = [':DOI: {doi}', ':URL: {url}', ':AUTHORS: {authors}']
    if attached_file_name is not None:
        header += 'ATTACH:'
        properties.extend([':Attachments: %s' % attached_file_name, ':ID: %s' % attached_file_hash])
    org_str = '''%s
:PROPERTIES:
%s
:END:
***** Summary
***** Notes
***** Open Questions [/]
***** BibTeX
#+BEGIN_SRC bib :tangle bibliography.bib
{bibtex}#+END_SRC''' % (header, '\n'.join(properties))
    title = get_title(bib)
    authors = get_authors(bib)
    doi = get_doi(bib)
    url = get_url(bib)
    bibtex = get_bibtex(bib)
    return trailing_white_spaces_reg.sub('\n', org_str.format(
            title=title,
            doi=doi,
            url=url,
            authors=authors,
            bibtex=bibtex,
    ))

def generate_file_name(old_name, entry):
    title = get_title(entry)
    extension = os.path.splitext(old_name)[1]
    if extension == '':
        extension = '.pdf' # PDF by default?
    return title.replace(' ', '_') + extension

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == '--attach' and len(sys.argv) == 2:
        sys.exit('Syntax: %s <doi>\n')
    attach = sys.argv[1] == '--attach'
    if attach:
        args = sys.argv[2:]
    else:
        args = sys.argv[1:]
    try:
        config = get_config()
    except FileNotFoundError:
        sys.exit('No configuration file found. Please add a %s file somewhere.' % CONFIG_FILE)
    except ConfigError as e:
        sys.exit('Error with the configuration file: %s' % e)
    orgfile = config[CONFIG_ORGFILE_KEY]
    bib_entries = process_args(args, attach)
    output = []
    for entry, attached_file in bib_entries:
        if attach:
            name, obj = attached_file
            file_name = generate_file_name(name, entry)
            file_hash = attach_file(name, orgfile, file_name)
            output.append(orgmode_from_bibentry(entry, file_name, file_hash))
            if obj is not None:
                obj.close()
        else:
            output.append(orgmode_from_bibentry(entry))
    output = '\n'.join(output)
    with open(orgfile, 'a') as f:
        f.write(output)
        f.write('\n')

#!/usr/bin/env python3

import sys
import requests
import re
import os
import yaml
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

def process_args(args):
    entries = []
    for arg in args:
        new_entries = split_bib(generic_get_bib(arg))
        entries.extend(new_entries)
    return entries

org_str = '''**** UNREAD {title}\t:PAPER:
:PROPERTIES:
:DOI: {doi}
:URL: {url}
:AUTHORS: {authors}
:END:
***** Summary
***** Notes
***** Open Questions [/]
***** BibTeX
#+BEGIN_SRC bib :tangle bibliography.bib
{bibtex}#+END_SRC'''

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
    return bib.to_string('bibtex')

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

trailing_white_spaces_reg = re.compile('\s*\n') # to remove the whitespaces at the end of the lines

def orgmode_from_bibentry(bib):
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

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Syntax: %s <doi>' % sys.argv[0])
    try:
        config = get_config()
    except FileNotFoundError:
        sys.exit('No configuration file found. Please add a %s file somewhere.' % CONFIG_FILE)
    except ConfigError as e:
        sys.exit('Error with the configuration file: %s' % e)
    bib_entries = process_args(sys.argv[1:])
    output = []
    for entry in bib_entries:
        output.append(orgmode_from_bibentry(entry))
    output = '\n'.join(output)
    with open(config[CONFIG_ORGFILE_KEY], 'a') as f:
        f.write(output)
        f.write('\n')

#!/usr/bin/env python3

import sys
import requests
import re
import pybtex.database  # https://pypi.python.org/pypi/pybtex/
import pyperclip        # https://pypi.python.org/pypi/pyperclip

# Note: to get a JSON instead of a bibtex entry, use head = {'Accept': 'application/vnd.citationstyles.csl+json'}
def bibtex_from_doi(doi):
    url = 'http://dx.doi.org/%s' % doi
    head = {'Accept': 'application/x-bibtex'}
    req = requests.get(url, headers=head)
    assert req.status_code == 200
    return req.text

class BibError(Exception):
    pass

def bib_from_doi(doi):
    bib = pybtex.database.parse_string(bibtex_from_doi(doi), bib_format='bibtex')
    if len(bib.entries) == 0:
        raise BibError('Unknown doi: %s' % doi)
    assert len(bib.entries) == 1
    return bib

def bib_from_file(filename):
    try:
        with open(filename) as f:
            return pybtex.database.parse_file(f)
    except FileNotFoundError:
        raise BibError('Unknown file: %s' % filename)

def split_bib(bib):
    entries = []
    for key, value in bib.entries.items():
        entries.append(pybtex.database.BibliographyData({key : value}))
    return entries

def process_args(args):
    entries = []
    for arg in args:
        try: # is this a bibtex file ?
            subentries = split_bib(bib_from_file(arg))
        except BibError: # apparently not, maybe a DOI?
            try:
                subentries = [bib_from_doi(arg)]
            except (BibError, AssertionError): # ok, don't know what this is...
                sys.exit('Error with argument %s: neither a bibtex file nor a DOI.' % arg)
        entries.extend(subentries)
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
    bib_entries = process_args(sys.argv[1:])
    output = []
    for entry in bib_entries:
        output.append(orgmode_from_bibentry(entry))
    output = '\n'.join(output)
    pyperclip.copy(output)
    print(output)

#!/usr/bin/env python3

import sys
import requests
import pybtex.database # https://pypi.python.org/pypi/pybtex/

def bibtex_from_doi(doi):
    url = 'http://dx.doi.org/%s' % doi
    head = {'Accept': 'application/x-bibtex'}
    req = requests.get(url, headers=head)
    assert req.status_code == 200
    return req.text

def bib_from_doi(doi):
    bib = pybtex.database.parse_string(bibtex_from_doi(doi), bib_format='bibtex')
    assert len(bib.entries) == 1
    return bib


org_str = '''**** UNREAD {title}
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
{bibtex}
#+END_SRC'''

def get_entry(bib): # suppose one and only one entry
    return bib.entries.values()[0]

def get_title(bib):
    return get_entry(bib).fields['title']

def get_doi(bib):
    return get_entry(bib).fields['doi']

def get_bibtex(bib):
    return bib.to_string('bibtex')

def get_url(bib):
    return get_entry(bib).fields['url']

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

def orgmode_from_bibentry(bib):
    title = get_title(bib)
    authors = get_authors(bib)
    doi = get_doi(bib)
    url = get_url(bib)
    bibtex = get_bibtex(bib)
    return org_str.format(
            title=title,
            doi=doi,
            url=url,
            authors=authors,
            bibtex=bibtex,
    )

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Syntax: %s <doi>' % sys.argv[0])
    print(orgmode_from_bibentry(bib_from_doi(sys.argv[1])))

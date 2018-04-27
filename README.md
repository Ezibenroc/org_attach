# Org\_attach

[![Build Status](https://travis-ci.org/Ezibenroc/DOI_to_org.svg?branch=master)](https://travis-ci.org/Ezibenroc/DOI_to_org)

## Installation

```sh
./setup.py install --user
```

Create a file configuration file `.orgattachrc` in your working directory or one of its parent directories. Please refer
to [the example file](example_orgattachrc.yaml).

You can also create a global configuration file in `~/.config/orgattach/orgattachrc`.

## Usage

```sh
org_attach {bib,ipynb} entries [entries ...]
```

The syntax for the entries depends on the command (`bib` or `ipynb`). The script will add a new entry in the org file
according to the template specified in the configuration file. It will also attach the given file (when relevant).

- **Bibliographical entry** (`bib`):
    An entry is made of two arguments separated by a comma. The first argument is mandatory, it is an identifier for a
    bibtex file. The second argument is optionnal, it is an identifier for any file (usually the corresponding PDF) that
    should be attached.
    Note that if no attachment file is specified, the script will try do fetch the file specified by the `PDF` field of
    the bibtex file (if there is one).
- **Jupyter notebook entry** (`ipynb`):
    An entry is made of one mandatory argument, an identifier for a jupyter notebook file that should be attached.

An identifier for any file can be a path in your file system or a URL. An identifier for a bibtex file can _also_ be a
DOI or an IdHAL.

## Examples

Add three entries for the given DOI.
```sh
org_attach bib 10.1137/0206024 10.1145/357172.357176 10.1145/321033.321034
```

Add an entry for the given DOI and attach the given file.
```sh
org_attach bib 10.1137/0206024,/path/to/the/file.pdf
```

Same thing, but the file is passed as an URL instead of a path.
```sh
org_attach bib 10.1137/0206024,http://somewebsite.com/path/to/the/file.pdf
```

This time, the bibtex file is passed as a path.
```sh
org_attach bib /path/to/some/biblio.bib
```

The bibtex file can be passed as a URL. Note that for this specific example, the bibtex file has a `PDF` field, so the
paper will be attached automatically.
```sh
org_attach bib https://hal.inria.fr/hal-01017319v2/bibtex
```

Equivalent to the previous example, but using the IdHAL instead of the URL.
```sh
org_attach bib hal-01017319v2
```

Attaching a Jupyter notebook file specified by a path.
```sh
org_attach ipynb /path/to/the/file.ipynb
```

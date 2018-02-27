# Py\_doi

## Installation

```sh
pip3 install --user pybtex
pip3 install --user python-magic
git clone https://github.com/Ezibenroc/DOI_to_org.git
```

Create a file `.doirc` in your working directory or one of its parent directories. The syntax of this file is:
```yaml
orgfile: /path/to/your/org/file
```
You can also create a global configuration file in `~/.config/doi2org/.doirc`

## Basic usage

```sh
python3 doi_to_org.py ARG1 ARG2 ARG3 ARG4 ...
```

Each argument can either be a DOI, the path to a bibtex file, the URL to a bibtex file or a HAL identifier.

Typing `python3` everytime is tedious. We hence suggest that you install an alias somewhere in your $PATH, for instance like this:

```sh
ln -s <full-path-to-doi_to_org.py> ~/bin/doi2org
```
You can then simply type doi2org.

It will append the result to the org file that is specified in the `.doirc` file.

Example:
```sh
python3 doi_to_org.py 10.1137/0206024 10.1145/357172.357176 10.1145/321033.321034
```

Result:
```org
**** UNREAD Fast Pattern Matching in Strings
:PROPERTIES:
:DOI: 10.1137/0206024
:URL: https://doi.org/10.1137%2F0206024
:AUTHORS: Donald E. Knuth, Jr. James H. Morris, Vaughan R. Pratt
:END:
***** Summary
***** Notes
***** Open Questions [/]
***** BibTeX
#+BEGIN_SRC bib :tangle bibliography.bib
@article{Knuth_1977,
    author = "Knuth, Donald E. and James H. Morris, Jr. and Pratt, Vaughan R.",
    doi = "10.1137/0206024",
    url = "https://doi.org/10.1137\%2F0206024",
    year = "1977",
    month = "jun",
    publisher = "Society for Industrial {\\&} Applied Mathematics ({SIAM})",
    volume = "6",
    number = "2",
    pages = "323--350",
    title = "Fast Pattern Matching in Strings",
    journal = "{SIAM} Journal on Computing"
}
#+END_SRC
**** UNREAD The Byzantine Generals Problem
:PROPERTIES:
:DOI: 10.1145/357172.357176
:URL: https://doi.org/10.1145%2F357172.357176
:AUTHORS: Leslie Lamport, Robert Shostak, Marshall Pease
:END:
***** Summary
***** Notes
***** Open Questions [/]
***** BibTeX
#+BEGIN_SRC bib :tangle bibliography.bib
@article{Lamport_1982,
    author = "Lamport, Leslie and Shostak, Robert and Pease, Marshall",
    doi = "10.1145/357172.357176",
    url = "https://doi.org/10.1145\%2F357172.357176",
    year = "1982",
    month = "jul",
    publisher = "Association for Computing Machinery ({ACM})",
    volume = "4",
    number = "3",
    pages = "382--401",
    title = "The Byzantine Generals Problem",
    journal = "{ACM} Transactions on Programming Languages and Systems"
}
#+END_SRC
**** UNREAD A Computing Procedure for Quantification Theory
:PROPERTIES:
:DOI: 10.1145/321033.321034
:URL: https://doi.org/10.1145%2F321033.321034
:AUTHORS: Martin Davis, Hilary Putnam
:END:
***** Summary
***** Notes
***** Open Questions [/]
***** BibTeX
#+BEGIN_SRC bib :tangle bibliography.bib
@article{Davis_1960,
    author = "Davis, Martin and Putnam, Hilary",
    doi = "10.1145/321033.321034",
    url = "https://doi.org/10.1145\%2F321033.321034",
    year = "1960",
    month = "jul",
    publisher = "Association for Computing Machinery ({ACM})",
    volume = "7",
    number = "3",
    pages = "201--215",
    title = "A Computing Procedure for Quantification Theory",
    journal = "Journal of the {ACM}"
}
#+END_SRC
```

## Power user

```sh
python3 doi_to_org.py ARG1,FILE1 ARG2,FILE2 ARG3,FILE3 ARG4,FILE4 ...
```

It will add an entry in the org-file for each of the arguments, as before. It will also attach
the file FILEi to the entry that was added for ARGi. FILEi has to be the path to a file on the
system or an URL to a file.

Note that if an attachment file is not specified but the bibliographical entry has a `PDF` field,
the script will try to download this PDF and attach it.

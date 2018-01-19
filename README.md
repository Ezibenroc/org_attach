# Py\_doi

## Installation

```sh
pip3 install --user pybtex
pip3 install --user pyperclip
git clone https://github.com/Ezibenroc/DOI_to_org.git
```

## Usage

```sh
python3 doi_to_org.py DOI1 DOI2 DOI3 DOI4 ...
```

It will print the result to the terminal and copy it to your clipboard. Hence, if you wish
to use it in an org-mode file, you do not have to manually copy it.

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

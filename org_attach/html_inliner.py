import sys
import base64
import os
from bs4 import BeautifulSoup

def get_file_content(filename):
    with open(filename) as f:
        content = ''.join(f.readlines())
    return content

def parse_file(filename):
    return BeautifulSoup(get_file_content(filename), 'lxml')

def dump_file(filename, soup):
    with open(filename, 'w') as f:
        f.write(str(soup))

def iter_css(soup):
    for elt in soup.find_all('link'):
        if elt.get('rel') == ['stylesheet'] and elt.get('type') == 'text/css' and 'href' in elt.attrs:
            yield elt

def inline_css(soup):
    for css in iter_css(soup):
        print(css)
        content = get_file_content(css.get('href'))
        newtag = soup.new_tag('style')
        newtag['type'] = 'text/css'
        newtag.string = content
        css.replaceWith(newtag)

def iter_js(soup):
    for elt in soup.find_all('script'):
        if elt.get('type') == 'text/javascript' and 'src' in elt.attrs:
            yield elt

def inline_js(soup):
    for js in iter_js(soup):
        print(js)
        content = get_file_content(js.get('src'))
        newtag = soup.new_tag('script')
        newtag['type'] = 'text/javascript'
        newtag.string = content
        js.replaceWith(newtag)

def iter_img(soup):
    for elt in soup.find_all('img'):
        if 'src' in elt.attrs:
            yield elt

def inline_img(soup):
    for img in iter_img(soup):
        alt = img.get('alt', '')
        img_src = img.get('src')
        img_type = os.path.splitext(img_src)[1]
        if img_type != '':
            img_type = img_type[1:]
            with open(img_src, 'rb') as f:
                content = base64.b64encode(f.read()).decode('ascii')
            newtag = soup.new_tag('img')
            newtag['alt'] = alt
            newtag['src'] = 'data:image/%s;base64,%s' % (img_type, content)
            img.replaceWith(newtag)
        else:
            assert img_src.startswith('data:')

def inline_all(soup):
    inline_css(soup)
    inline_js(soup)
    inline_img(soup)

def inline_content(file_content):
    soup = BeautifulSoup(file_content, 'lxml')
    inline_all(soup)
    return str(soup)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.stderr.write('Syntax: %s <in_file> <out_file>\n' % sys.argv[0])
        sys.exit(1)
    in_file  = sys.argv[1]
    out_file = sys.argv[2]
    soup = parse_file(in_file)
    inline_all(soup)
    dump_file(out_file, soup)

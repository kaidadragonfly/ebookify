#!/usr/bin/env python
"""
Takes a json file with `titles` and `urls` at the top level and converts those
into an ebook version of the Magic story.

Dependencies:
  pip install requests bs4 lxml
"""
import os
import sys
import argparse
import json
import re
import requests

from bs4 import BeautifulSoup

if 'unicode' not in dir(__builtins__):
    unicode = str # pylint: disable=invalid-name

REALPATH = os.path.realpath(sys.argv[0])
ROOTPATH = os.path.dirname(REALPATH)
CACHEPATH = os.path.join(ROOTPATH, '.cache')

if not os.path.exists(CACHEPATH):
    os.makedirs(CACHEPATH)

def main():
    "Entry point!"
    parser = argparse.ArgumentParser(
        description="Download and ebookify the Magic story")
    parser.add_argument(
        'json',
        metavar="JSON",
        type=str,
        help="A JSON file specifying titles and URLs")
    args = parser.parse_args()
    with open(args.json) as file:
        config = json.loads(file.read())
        set_name = config['expansion']
        urls = [str(u) for u in config['urls']]

    book = BeautifulSoup("""
    <!DOCTYPE html>
    <html lang="en" xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
        <title>{set_name}: Collected Stories</title>
        <link rel="stylesheet" href="style.css"  type="text/css" />
      </head>
      <body>
        <div id="title-page">
          <h1>{set_name}</h1>
          <span>Collected Stories</span>
          <div id="disclaimer">
            <strong>Disclaimer</strong>
            <p>
              All stories are owned by Wizards of the Coast, this is intended
              merely to create a cache for personal use.
            </p>
          </div>
        </div>
        <div id="table-of-contents">
          <h2>Table of Contents</h2>
          <ol>
          </ol>
        </div>
      </body>
    </html>
    """.format(set_name=set_name), 'html.parser')

    htmlfile = args.json.replace('.json', '.html')
    ncxfile = args.json.replace('.json', '.ncx')
    opffile = args.json.replace('.json', '.opf')

    for url, idx in zip(urls, range(len(urls))):
        parse_chapter(book, url, idx + 1)

    with open(htmlfile, 'wb') as outfile:
        outfile.write(book.prettify().encode('utf-8'))

    with open(ncxfile, 'wb') as outfile:
        outfile.write(
            create_ncx_toc(book, htmlfile).prettify().encode('utf-8'))

    with open(opffile, 'wb') as outfile:
        outfile.write(
            create_opf(book, htmlfile, ncxfile).encode('utf-8'))

def create_opf(book, htmlfile, ncxfile):
    """
    Create the top level file to tie some of the pieces together.
    """
    return """
    <?xml version="1.0" encoding="utf-8"?>
    <package unique-identifier="{title}" xmlns:asd="http://www.idpf.org/asdfaf" xmlns:opf="http://www.idpf.org/2007/opf">
      <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>{title}</dc:title>
        <dc:language>en</dc:language>
        <dc:creator>Magic Creative Team</dc:creator>
        <dc:copyrights>Wizards of the Coast</dc:copyrights>
        <dc:publisher>Blind Eternities</dc:publisher>
        <meta name="cover" content="cover-image" />
      </metadata>
      <manifest>
        <item id="book" href="{htmlfile}" media-type="application/xhtml+xml"/>
        <item id="stylesheet" href="style.css" media-type="text/css"/>
        <item href="{ncxfile}" id="ncx" media-type="application/x-dtbncx+xml"/>
        <item id="cover-image" href="cover.jpg" media-type="image/jpeg" />
      </manifest>
      <spine toc="ncx">
        <itemref idref="book" />
      </spine>
      <guide>
        <reference href="aer.html#table-of-contents" title="Table of Contents" type="toc"/>
        <reference href="aer.html" title="Beginning" type="text"/>
      </guide>
    </package>
    """.format(
        title=book.title.text,
        htmlfile=htmlfile,
        ncxfile=ncxfile)

def create_ncx_toc(book, htmlfile):
    """
    Create the NCX formatted Table of Contents for `book`.
    """
    toc = BeautifulSoup("""
    <?xml version="1.0"?>
    <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
     "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
    <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
      <head>
      </head>
      <docTitle><title>{}</title></docTitle>
      <navMap>
        <navPoint id="table-of-contents" playOrder="1">
           <navLabel>
             <text>Table of Contents</text>
           </navLabel>
           <content src="{}#table-of-contents" />
        </navPoint>
      </navMap>
    </ncx>
    """.format(book.title.string, htmlfile), 'xml')

    chapters = book.find(id='table-of-contents').find('ol')
    nav_map = toc.find('ncx').find('navMap')

    play_order = 1
    for chapter in chapters.children:
        if chapter.name == 'li':
            play_order += 1
            link = chapter.find('a')
            ch_id = link['href'].replace('#', '')
            point = tag(toc, 'navPoint', '', id=ch_id, playOrder=play_order)
            label = tag(toc, 'navLabel')
            label.append(tag(toc, 'text', link.text))
            point.append(label)
            point.append(
                tag(toc, 'content', '', src="{}#{}".format(htmlfile, ch_id)))
            nav_map.append(point)

    return toc

def get_cached(url, binary=False):
    """
    Make a request (naively) caching on disk.

    If `binary` is true return the path instead of the content.
    """
    cachepath = os.path.join(CACHEPATH, re.sub('[:/]', '^', url))

    text = None
    if os.path.exists(cachepath):
        if not binary:
            with open(cachepath) as cache:
                text = cache.read()
    else:
        resp = requests.get(url)

        with open(cachepath, 'wb') as cache:
            if binary:
                cache.write(resp.content)
            else:
                text = resp.text
                cache.write(text.encode('utf-8'))

    if binary:
        response = os.path.relpath(cachepath, ROOTPATH)
    else:
        response = text

    return response

def parse_chapter(book, url, ch_num):
    """
    Parse an individual chapter into the book.
    """
    html = BeautifulSoup(get_cached(url), 'html.parser')

    title = re.sub(r' \| [^|]*', '', html.title.string)
    title_id = title.replace(' ', '-').lower()

    author = html.find_all('div', class_='author')[0].find('p').string
    content = html \
              .find(id='content-detail-page-of-an-article') \
              .body
    children = []

    for child in content.children:
        author = parse_child(book, children, child, author)

    if children[-1].name == 'hr':
        children = children[0:-1]
    contents = book.find(id='table-of-contents')
    item = tag(book, 'li')
    contents.find('ol').append(item)
    item.append(tag(book, 'a', title, href=('#' + title_id)))

    chapter_header = tag(book, 'div', '', {"class": 'ch-header'})
    book.body.append(chapter_header)
    chapter_header.append(
        tag(book, 'span', ch_num))
    chapter_title = tag(book, 'h2', id=title_id)
    chapter_title.append(tag(book, 'a', title, href=url))
    chapter_header.append(chapter_title)
    chapter_header.append(
        tag(book, 'h3', author))

    for child in children:
        book.body.append(child)

def parse_child(book, children, child, author):
    """
    Parse out an individual child element.
    """
    if not child.name:
        return author

    if child.string and 'Stories written by' in child.string:
        author = child.string.replace('Stories written by', 'By')
        author = re.sub(r'[.]$', '', author)
        return author

    if child.text:
        text = child.text.lower()
        if 'previous story: ' in text \
           or 'previous episode: ' in text \
           or 'planeswalker profile' in text:
            return author

    for img in child.find_all('img'):
        img = child.find('img')
        src = get_cached(img['src'], binary=True)
        img['src'] = src

    if child.name == 'div':
        fig = child.find('figure')
        if fig:
            cap = fig.find('figcaption').text
            illustration = tag(book, 'div', '', {"class": "illustration"})
            illustration.append(tag(book, 'span', cap))
            children.append(illustration)

    if child.name in ['p', 'hr']:
        children.append(child)

    return author

def tag(soup, name, contents='', attrs=None, **kwargs):
    """
    Appends a tag to the body of the provided soup.
    """
    attrs = attrs or {}
    attrs.update(kwargs)

    new_tag = soup.new_tag(name, **attrs)
    new_tag.string = unicode(contents)

    return new_tag

if __name__ == "__main__":
    main()

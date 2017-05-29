# Ebookifier #

A tool to collect issues of the Magic Story into a `.mobi` ebook.

(Because Wizards seems like they've stopped doing these and I wanted
to read the story on my Kindle.)

When given a JSON file that an object with the keys `expansion`, that
is the name of the _Magic_ expansion and `urls` which is an array of
_Magic Story_ URLs (in order) it will create 4 files.

1. `.html`: This is the book itself, in HTML form.
2. `.ncx`: A table of contents KindleGen understands.
3. `.opf`: Packages the table of contents, cover and html together.

**Disclaimer**: This is intended entirely for personal use, and is
meant to only be used to create a cached/local copy of the story for
reading on your Kindle, not for redistribution.

PS: Please don't sue me...

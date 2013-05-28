import re
from collections import namedtuple
import lxml.html
import numpy
import langid

# Fix langid probability normalization
langid.langid.load_model()
langid.langid.identifier.norm_probs = lambda vals: numpy.exp(vals - numpy.logaddexp.reduce(vals))

Article = namedtuple('Article', 'url, id, lang, metadata, translations, source, title, entry')
url_pattern = re.compile('http://([a-z]+\.)?globalvoicesonline\.org')

block_elements = set(('address', 'blockquote', 'dd', 'div', 'dl', 'dt', 'dd',
    'fieldset', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
    'noscript', 'ol', 'p', 'pre', 'section', 'table', 'tfoot',
    'ul', 'li', 'video', 'br', 'center', 'img', 'tr', 'td', 'th'))

twitter = re.compile('(@|#)\w+')

def is_foreign(text, lang):
    plang, pconf = langid.classify(twitter.sub('', text))
    return (plang != lang or pconf < 0.9)

def is_foreign_quote(e, lang):
    cls = e.get('class')
    if cls in ('rtl', 'hebrew', 'arabic'): return True
    if e.tag == 'blockquote' or e.get('class') == 'translation':
        return is_foreign(e.text_content(), lang)
    return False

def _clean_foreign(e, lang):
    """
    Remove quotations which contain foreign language.
    Add new lines before/after block elements
    """
    for c in e:
        if c.tag in block_elements:
            c.text = ('\n'+c.text if c.text else '\n')
            c.tail = ('\n'+c.tail if c.tail else '\n')
        if is_foreign_quote(c, lang):
            yield c.text_content()
            e.remove(c)
        else:
            for removed in clean_foreign(c, lang):
                yield removed

def clean_foreign(e, lang):
    return list(_clean_foreign(e, lang))

def get_text(e, lang):
    clean_foreign(e, lang)
    return '\n'.join(line.strip() for line in e.text_content().split('\n') if line.strip())

def process_article(record):
    # Get URL
    url = record.url
    # Get language
    lang = url_pattern.match(record.url).group(1)
    lang = 'en' if not lang else lang[:-1]
    # Parse HTML
    payload = record.payload.read()
    body = payload[payload.find('\n\r\n'):]
    doc = lxml.html.document_fromstring(body.decode('utf8'))
    # Extract post title and ID
    h2_title = doc.cssselect('h2.post-title')
    assert len(h2_title) == 1, 'Cannot find title'
    h2_title = h2_title[0]
    post_id = int(h2_title.get('id').split('-')[1])
    title = h2_title.find('a').text.strip()
    # Extract post content
    div_entry = doc.cssselect('#main-wrapper div.entry')
    assert len(div_entry) == 1, 'Cannot find entry container (n={})'.format(len(div_entry))
    entry = get_text(div_entry[0], lang)
    # Extract source translation
    source_link = doc.cssselect('span.source-link > a')
    source = source_link[0].get('href') if source_link else url
    # Extract translations
    translations = [a.get('href') for a in doc.cssselect('div.post-translations a')]
    # Extract metadata
    meta = doc.body.get('class')
    return Article(url, post_id, lang, meta, ' '.join(translations), source, title, entry)

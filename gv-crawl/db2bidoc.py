import sys
import os
import re
import sqlite3
import argparse
from collections import namedtuple
import nltk
from articles import Article, url_pattern

id_pattern = re.compile('.*\?p=(\d+)$')

def find_translation_url(article, lang):
    for url in article.translations.split():
        m = url_pattern.match(url)
        if not m: continue
        l = m.group(1)
        l = 'en' if not l else l[:-1]
        l = 'en' if l in ('rising', 'advocacy') else l
        if l == lang:
            return url

def find_translation(article, lang, cur):
    src_url = find_translation_url(article, lang)
    if not src_url: return None
    m = id_pattern.match(src_url)
    if m:
        aid = int(m.group(1))
        cur.execute('select * from articles where id = ?', (aid,))
    else:
        cur.execute('select * from articles where url = ?', (src_url,))
    row = cur.fetchone()
    if row is not None:
        return Article(*row)

# Aggressive tokenizer
tokenizer = nltk.tokenize.RegexpTokenizer('(\w+|[^\s])')

def write_article(article, untok, tok):
    with open(untok, 'w') as f_untok, open(tok, 'w') as f_tok:
        paragraphs = article.entry.split('\n')
        paragraphs.insert(0, article.title.replace('\n', ' '))
        for paragraph in paragraphs:
            for sent in nltk.sent_tokenize(paragraph):
                f_untok.write(sent.encode('utf8')+'\n')
                f_tok.write(' '.join(tokenizer.tokenize(sent)).lower().encode('utf8')+'\n')

year_re = re.compile('s-y(\d{4})')
month_re = re.compile('s-m(\d{2})')
day_re = re.compile('s-d(\d{2})')

def date(article):
    y = year_re.search(article.metadata).group(1)
    m = month_re.search(article.metadata).group(1)
    d = day_re.search(article.metadata).group(1)
    return y+'-'+m+'-'+d

def main():
    parser = argparse.ArgumentParser(description='Write articles to disk for alignment')
    parser.add_argument('src_lang', help='source language - original [en]')
    parser.add_argument('trg_lang', help='target language - translated [sw]')
    parser.add_argument('database', help='database path to read articles from')
    parser.add_argument('target_dir', help='target directory to write articles to')
    args = parser.parse_args()

    conn = sqlite3.connect(args.database)
    trg_cur = conn.cursor()
    src_cur = conn.cursor()

    def article_pairs(trg_lang, src_lang):
        trg_cur.execute('select * from articles where lang = ?', (trg_lang,))
        for article in trg_cur.fetchall():
            trg_article = Article(*article)
            src_article = find_translation(trg_article, src_lang, src_cur)
            yield trg_article, src_article

    main_dir = args.target_dir+'/corpus_to_align'
    src_untok = main_dir+'/source_language_corpus_untokenized/'
    src_tok = main_dir+'/source_language_corpus_prepared/'
    trg_untok = main_dir+'/target_language_corpus_untokenized/'
    trg_tok = main_dir+'/target_language_corpus_prepared/'
    align_info = main_dir+'/align_info.txt'

    for d in (main_dir, src_untok, src_tok, trg_untok, trg_tok):
        if not os.path.exists(d):
            os.mkdir(d)

    found, not_found = 0, 0
    with open(align_info, 'w') as f_align:
        for (trg, src) in article_pairs(args.trg_lang, args.src_lang):
            if not src:
                not_found += 1
                continue
            found += 1
            article_id = str(trg.id)
            write_article(src, src_untok+article_id+'.txt', src_tok+article_id+'.txt')
            write_article(trg, trg_untok+article_id+'.txt', trg_tok+article_id+'.txt')
            f_align.write('{}\t{}\t{}\t{}\n'.format(article_id, src.url, trg.url, date(trg)))

    print('Articles with translation written to disk: {}/{}'.format(found, found+not_found))

if __name__ == '__main__':
    main()

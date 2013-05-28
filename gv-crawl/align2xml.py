import argparse
from itertools import izip
from xml.sax.saxutils import escape
import re

def read_documents(align_dir):
    sentences = []
    previous_id = None
    with open(align_dir+'/aligned_sentences_source_language.txt') as f_src,\
            open(align_dir+'/aligned_sentences_target_language.txt') as f_trg,\
            open(align_dir+'/info.txt') as f_align_info:
        for src, trg, align_info in izip(f_src, f_trg, f_align_info):
            line_article_id = int(align_info.split('\t')[0][:-4])
            if previous_id is not None and line_article_id != previous_id:
                yield previous_id, sentences
                sentences = []
            sentences.append((src.decode('utf8').strip(), trg.decode('utf8').strip()))
            previous_id = line_article_id
    if previous_id is not None:
        yield previous_id, sentences

ALNUM = re.compile('[\W_\d]', re.UNICODE)
LANG = re.compile(' \[(aym|ay|id|ca|da|de|es|fr|fil|it|mg|hu|nl|pt|sr|sv|sw|pl|el|bg|mk|ru|ar|bn|ko|zh|jp|ja|en|cs|ro|sk|hr|fa|tr|uk|Fr|rus)\]')

def should_keep(text):
    if len(text) < 4: return False
    r = len(ALNUM.sub('', text.replace(' ', 'a')))/float(len(text))
    if r < 0.8: return False
    return True

def main():
    parser = argparse.ArgumentParser(description='Convert aligned articles to XML')
    parser.add_argument('src_lang', help='ISO code for source language - original [eng]')
    parser.add_argument('trg_lang', help='ISO code for target language - translated [swa]')
    parser.add_argument('info_file', help='align_info.txt file path')
    parser.add_argument('align_dir', help='output_data_aligned directory')
    args = parser.parse_args()

    src_lang = args.src_lang
    trg_lang = args.trg_lang

    doc_info = {}
    with open(args.info_file) as f_doc_info:
        for line in f_doc_info:
            article_id, src_url, trg_url, date = line[:-1].split('\t')
            article_id = int(article_id)
            doc_info[article_id] = (src_url, trg_url, date)

    print('<?xml version="1.0" encoding="utf-8"?>')
    print('<dataset>')
    for article_id, sentences in read_documents(args.align_dir):
        print('<file languages="{},{}" id="{}">'.format(src_lang, trg_lang, article_id))
        src_url, trg_url, date = doc_info[article_id]
        print('<metadata url_{}="{}" url_{}="{}" date="{}"/>'.format(src_lang,
            src_url, trg_lang, trg_url, date))
        print('  <data>')
        for i, (src_sentence, trg_sentence) in enumerate(sentences, 1):
            if not (should_keep(src_sentence) and should_keep(trg_sentence)):
                continue
            src_sentence = LANG.sub('', src_sentence)
            trg_sentence = LANG.sub('', trg_sentence)
            print('    <unit sentence="{}">'.format(i))
            print('      <align>')
            for lang, sentence in ((src_lang, src_sentence), (trg_lang, trg_sentence)):
                print('        <text langid="{}">'.format(lang))
                print('          <s>{}</s>'.format(escape(sentence).encode('utf8')))
                print('        </text>')
            print('      </align>')
            print('    </unit>')
        print('  </data>')
        print('</file>')
    print('</dataset>')

if __name__ == '__main__':
    main()

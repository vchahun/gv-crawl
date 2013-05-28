import os
import glob
import argparse
import logging
import warc
import sqlite3
from articles import Article, process_article

create_statement = """create table articles(url text primary key,
                                             id int,
                                             lang char(3),
                                             metadata text,
                                             translations text,
                                             source text,
                                             title text,
                                             entry text)"""

insert_statement = ('insert into articles('+', '.join(Article._fields)
        +') values ('+', '.join(['?']*len(Article._fields))+')')

def main():
    parser = argparse.ArgumentParser(description='Load articles into database from WARC files')
    parser.add_argument('warcs', nargs='+', help='WARC files to load from')
    parser.add_argument('database', help='database path to insert articles into')
    parser.add_argument('--table', default='global_voices',
            help='table name to insert articles into')
    parser.add_argument('--error', action='store_true',
            help='show errors while processing')
    args = parser.parse_args()

    logging.basicConfig(level=(logging.WARNING if args.error else logging.CRITICAL))

    db_exists = os.path.exists(args.database)
    conn = sqlite3.connect(args.database)
    cur = conn.cursor()

    if not db_exists:
        cur.execute(create_statement)
        conn.commit()

    def article_records():
        for fn in args.warcs:
            n_records = n_errors = 0
            print('Processing {}'.format(fn))
            warc_file = warc.open(fn)
            previous_offset = warc_file.tell()
            for record in warc_file:
                n_records += 1
                try:
                    yield process_article(record)
                except AssertionError as e:
                    n_errors += 1
                    logging.error('{}\t{}'.format(record.url, e))
            warc_file.close()
            print('Records processed: {} ({} errors => {} inserted)'.format(n_records,
                n_errors, n_records - n_errors))

    cur.executemany(insert_statement, article_records())
    conn.commit()

if __name__ == '__main__':
    main()

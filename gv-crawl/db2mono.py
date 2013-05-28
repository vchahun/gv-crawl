import sqlite3
import argparse
from util import Article

def main():
    parser = argparse.ArgumentParser(description='Dump all text')
    parser.add_argument('database', help='database to read articles from')
    parser.add_argument('lang', help='language to get articles for')
    args = parser.parse_args()

    conn = sqlite3.connect(args.database)
    cur = conn.cursor()

    cur.execute('select * from articles where lang = ?', (args.lang,))

    for article in cur.fetchall():
        article = Article(*article)
        print article.entry

if __name__ == '__main__':
    main()

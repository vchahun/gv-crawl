import sqlite3
import argparse
from util import Article
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(description='Dump all text')
    parser.add_argument('database', help='database to read articles from')
    parser.add_argument('lang', help='language to get articles for')
    args = parser.parse_args()

    conn = sqlite3.connect(args.database)
    cur = conn.cursor()

    cur.execute('select metadata from articles where lang = ?', (args.lang,))
    print('Total: {}'.format(cur.rowcount))

    years = defaultdict(lambda: defaultdict(list))

    for (meta,) in cur.fetchall():
        if not meta: continue
        m = {}
        for item in meta.split():
            if item[:3] in ('s-y', 's-m', 's-d'):
                m[item[2]] = int(item[3:])
        years[m['y']][m['m']].append(m['d'])

    for y, months in sorted(years.iteritems()):
        y_total = sum(map(len, months.itervalues()))
        m_info = ', '.join('{:0>2}: {}'.format(m, len(days))
                for m, days in sorted(months.iteritems()))
        print('{}: {} | {}'.format(y, y_total, m_info))

if __name__ == '__main__':
    main()

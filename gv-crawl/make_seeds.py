#!/usr/bin/env python
import sys
import lxml.etree as et

def main():
    feed = et.parse(sys.stdin)
    for link in feed.findall('//item/link'):
        print(link.text)

if __name__ == '__main__':
    main()

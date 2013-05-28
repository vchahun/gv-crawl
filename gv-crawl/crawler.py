#!/usr/bin/env python
#
# Copyright 2012 Juan Manuel Caicedo Carvajal (http://cavorite.com).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
A stand-alone spider for Scrapy that saves the downloaded in Warc archives.
'''
import os
import datetime
import httplib
import argparse
import anydbm
import fileinput
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import warc
import w3lib.url

import scrapy.cmdline
from scrapy.signalmanager import SignalManager
from scrapy.item import BaseItem
from scrapy import log, signals

from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule


class WarcWriter(object):
    '''Writes `Response` objects into warc files on a given directory.'''
    def __init__(self, outdir, max_mb_size=100, fname_prefix='scrapy'):
        '''
        `outdir`  Output directory
        `max_mb_size`   Maximum size of the Warc files. When the current file 
                        exceeds this limit, a new file is created.
        `fname_prefix`  Prefix used to name the warc files.


        The output directory is also used to add an index
        file to avoid duplicated entries in the Warc files.
        '''
        self.max_size = max_mb_size * 1024 * 1024
        self.outdir = outdir
        self.fname_prefix = fname_prefix
        
    def _get_warc_file(self):
        '''Creates a new Warc file'''
        assert self.warc_fp is None, 'Current Warc file must be None'

        self.file_n += 1
        fname = '%s.%s.warc.gz' % (self.fname_prefix, self.file_n)
        self.warc_fname = os.path.join(self.outdir, fname)
        self.warc_fp = warc.open(self.warc_fname, 'w')

    def open(self, spider):
        self.file_n = spider.state.get('warc_n_start', 0)
        log.msg('Loading state: %d' % self.file_n)

        # Create a new warc.gz file
        self.warc_fp = None
        self._get_warc_file()

        # Create the db index
        db_fname = os.path.join(self.outdir, '.job', 'index.db')
        self.db = anydbm.open(db_fname, 'c') # FIXED to not overwrite

    def close(self, spider):
        self.db.close()
        if not self.warc_fp is None:
            self.warc_fp.close()

    def write_response(self, response):
        '''Writes a `response` object from Scrapy as a Warc record. '''
        # Avoid duplicated entries
        response_url = w3lib.url.safe_download_url(response.url)
        if response_url in self.db:
            log.msg('Ignored already stored response: %s' % response_url, level=log.DEBUG)
            return
        self.db[response_url] = '1'

        # Create the payload string
        payload = StringIO.StringIO()
        status_reason = httplib.responses.get(response.status, '-')
        payload.write('HTTP/1.1 %d %s\r\n' % (response.status, status_reason))
        for h_name in response.headers:
            payload.write('%s: %s\n' % (h_name, response.headers[h_name]))

        payload.write('\r\n')
        payload.write(response.body)

        headers = {
            'WARC-Type': 'response',
            'WARC-Date': WarcWriter.now_iso_format(),
            'Content-Length': str(payload.tell()),
            'Content-Type': str(response.headers.get('Content-Type', '')),

            # Optional headers
            'WARC-Target-URI': response_url
        }
        record = warc.WARCRecord(payload=payload.getvalue(), headers=headers)

        self._write_record(record)

    def _write_record(self, record):
        '''Writes a record in the current Warc file.

        If the current file exceeds the limit defined by `self.max_size`, the
        file is closed and a new one is created.
        '''
        self.warc_fp.write_record(record)

        curr_pos = self.warc_fp.tell()
        if curr_pos > self.max_size:
            self.warc_fp.close()
            self.warc_fp = None
            self._get_warc_file()

    @staticmethod
    def now_iso_format():
        '''Returns a string with the current time according to the ISO8601 format'''
        now = datetime.datetime.utcnow()
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")


class WarcSpider(CrawlSpider):
    '''Stand-alone spider that stores pages in a WARC file'''
    name = 'warc'
    start_urls = []
    allowed_domains = []

    def __init__(self, seeds=None, outdir=None, domains=None):
        '''
        `seeds`       Text file containing the seed URLs. One URL per line.
        `outdir`      Output directory
        `domains`     Comma separated list of allowed domains.
        '''

        # FIXED this way no need to compile after init
        WarcSpider.rules = [Rule(SgmlLinkExtractor(allow=r'.*', tags='link',
            restrict_xpaths=('//link[@rel="prev"]', '//link[@rel="next"]')),
            callback='archive_page', follow=True)]

        super(WarcSpider, self).__init__()

        # Valiadate arguments
        assert not outdir is None, 'Argument `outdir` is mandatory'
        assert not seeds is None, 'Argument `seeds` is mandatory'
        if domains:
            self.allowed_domains = domains.split(',')

        # FIXME: Validate settings
        #assert settings['DOWNLOAD_DELAY'] > 0, 'download_delay must be greater than 0'

        self.writer = WarcWriter(outdir)

        # Load the seeds
        WarcSpider.start_urls = WarcSpider.load_seeds(seeds)

    # FIXED register properly with crawler (close was not called previously)
    def set_crawler(self, crawler):
        super(WarcSpider, self).set_crawler(crawler)
        # Configure signals
        crawler.signals.connect(self.writer.open, signals.spider_opened)
        crawler.signals.connect(self.writer.close, signals.spider_closed)

    def archive_page(self, response):
        '''Callback function that stores a response as a WARC record.'''
        self.writer.write_response(response)
        log.msg('Response added to Warc: %s' % response.url, level=log.DEBUG)
        self.state['warc_n_start'] = self.writer.file_n

    # FIXED avoid duplicate archive and overrinding _parse_response
    def parse_start_url(self, response):
        '''Initial callback function for seeds'''
        self.archive_page(response)

    @staticmethod
    def load_seeds(fname):
        '''Loads the seeds from a text file.

        It ignores empty lines and lines starting with a '#'.
        '''
        data = fileinput.input([fname], openhook=fileinput.hook_compressed)
        for line in data:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            yield line

        data.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--delay',  type=int, default=1)
    parser.add_argument('--depth', type=int, default=0)
    parser.add_argument('--domains', '-d')
    parser.add_argument('--user_agent')
    parser.add_argument('--silent', action='store_true', default=False)
    parser.add_argument('--loglevel', choices=('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'))

    parser.add_argument('seeds')
    parser.add_argument('outdir')

    args = parser.parse_args()

    # FIXED added job dir for state persistence
    jobdir = os.path.join(args.outdir, '.job')
    argv = ('scrapy runspider -s AUTOTHROTTLE_ENABLED=1 '
    '-s DEPTH_LIMIT={} -s DOWNLOAD_DELAY={} -s JOBDIR={}').format(args.depth, args.delay, jobdir)
    argv = argv.split(' ')
    if args.user_agent:
        argv.extend(['-s', 'USER_AGENT="%s"' % args.user_agent])

    if args.silent:
        argv.extend(['-s', 'LOG_ENABLED=False'])

    if args.loglevel:
        argv.extend(['-s', 'LOG_LEVEL=%s' % args.loglevel])

    argv.append(__file__)
    argv.extend(['-a', 'outdir=%s' % args.outdir])
    argv.extend(['-a', 'seeds=%s' % args.seeds])
    if args.domains:
        argv.extend(['-a', 'domains=%s' % args.domains])

    scrapy.cmdline.execute(argv=argv)

if __name__ == '__main__':
    main()

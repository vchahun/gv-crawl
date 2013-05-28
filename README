# Parallel text extraction from GlobalVoices

[GlobalVoices](http://globalvoicesonline.org) is a community of bloggers and citizen journalists writing and translating news articles in several languages. We crawl articles from this website to create parallel corpora for low-resource languages.

## Requirements

Python 2.7 is required. Install dependencies with:

    pip install -r requirements.txt

## Step 1 (up to 1 week): crawl articles from the website

We can obtain seed URLs from the RSS feeds. It is recommended to add more seeds at different starting dates if starting to crawl from scratch. The crawler will follow the previous and next article links on each page.

For example, to crawl the [Malagasy version](http://mg.globalvoicesonline.org) of the website, run:

	mkdir crawl-mg
	curl http://mg.globalvoicesonline.org/feed/ | python gv-crawl/make_seeds.py > crawl-mg/seeds.txt
	python gv-crawl/crawler.py crawl-mg/seeds.txt crawl-mg --delay 1 2> crawl-mg/crawl.log

The crawling can be interrupted and restarted; it should resume operation automatically. This also permits incremental crawling.

Compressed WARC files containing the crawled pages are created.

## Step 2 (up to 1h): create article database

After we have crawled several versions of the website, we can find parallel documents for a pair of languages. Fist, we insert all articles in a database (repeat for all languages):

    python gv-crawl/warc2db.py ./crawl-mg/scrapy.*.warc.gz articles.db

## Step 3: sentence alignment

Then, we use Gargantua to align the sentences:

	python gv-crawl/db2bidoc.py en mg articles.db $(GARGANTUA)
	cd $(GARGANTUA) && mkdir corpus_data && cd corpus_data && ../src/sentence-aligner

## Step 4: create aligned XML bitext

	python gv-crawl/align2xml.py eng mlg\
		$(GARGANTUA)/corpus_to_align/align_info.txt\
		$(GARGANTUA)/corpus_data/output_data_aligned > en-mg.xml

# License

Copyright (c) 2013, [Victor Chahuneau](http://victor.chahuneau.fr/)

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

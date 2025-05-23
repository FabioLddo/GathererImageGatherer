# GathererImageGatherer

This project downloads all the card images from [gatherer.wizards.com](http://gatherer.wizards.com/Pages/Default.aspx) and saves them in the folder cardImages/ with their name and set.

The images can be used to build a database of perceptual hashes. Since each card artwork has a unique perceptual hash, they can be compared with perceptual hashes of a card in a picture to identify them. If a card is identified, the information can be input into http://shop.tcgplayer.com/magic for the user to quickly get the price.

## Dependencies

To run these programs you will need the python libraries BeautifulSoup, requests, imagehash, PIL, and psycopg2.

<pre>
    $> pip install -r requirements.txt
    or
    $> conda env create -f environment.yml
</pre>

<pre>
    git clone https://github.com/eulerto/pg_similarity.git
    cd pg_similarity/
    USE_PGXS=1 make
    USE_PGXS=1 make install
</pre>

In postgres:
<pre>
    CREATE EXTENSION pg_similarity;
</pre>

## Use

**Download Images**

<pre>
    python scrapeImages.py
</pre>

This downloads all the card images from http://gatherer.wizards.com/Pages/Default.aspx and saves them in the folder cardImages/ with their name and set.

The folder of pictures ends up being 1.21 GB and it takes about 25 minutes to download.

**Setup The Database**

Once postgres is installed, create a database and table needed for the python script.
<pre>
    psql
    create database cardimages;
    \c cardimages
    create table phash(name text, set text, hash text);
</pre>

**Build The Database**

<pre>
    $> python buildDatabase.py
</pre>

Populates a postgresql database with card name, set, and a perceptual hash of the artwork from the images downloaded with scrapeImages.py

**Test A Card**

<pre>
    $> python queryDatabase.py
</pre>

## TODOs

- [x] Reorganize folders
- [x] Add Docker-Compose to develop without installing Postgres locally
- [x] Add a license (i.e. MIT)
- [x] Refactor the output paths to download
- [x] Add a way to resume downloads and avoid repetitions
- [x] Add a way to download from another sources (like ebay or google)
- [ ] Refactor the way to download files creating a subfolder by card
- [ ] Merge several ways to build the dataset
- [ ] Test all python scripts to check function after route refactor
- [ ] Finish Makefile
- [ ] Add a way to automatically launch sql script once
- [ ] Update README with makefile and new sections
- [ ] Add a notebook example

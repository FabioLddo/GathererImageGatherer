# GathererImageGatherer

This project downloads all the card images from http://gatherer.wizards.com/Pages/Default.aspx and saves them in the folder cardImages/ with their name and set

The images can be used to build a database of perceptual hashes.

https://en.wikipedia.org/wiki/Perceptual_hashing

Since each artwork has a unique hash, they can be compared with new pictures of cards to identify them. 

If a card is identified, the information can be input into a search engine for the user.

#Dependencies
To run these programs you will need the python libraries BeautifulSoup, requests, imagehash, PIL, and psycopg2. 
<pre>
pip install BeautifulSoup requests imagehash PIL psycopg2
</pre>
#Use
**Download Images**
<pre>
sudo python scrapeImages.py
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
sudo python buildDatabase.py
</pre>
Populates a postgresql database with card name, set, and a perceptual hash of the artwork from the images downloaded with scrapeImages.py

**Test A Card**
<pre>
sudo python queryDatabase.py
</pre>




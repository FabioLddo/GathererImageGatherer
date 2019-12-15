#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import yaml
import urllib
import requests
import os

# This fetches the first card from the page
def getFirstPic(url):
    result = requests.get(url)
    html = result.content
    soup = BeautifulSoup(html, "lxml")
    hold=soup.find("span", "cardTitle")
    if(hold):
        return hold.a.get_text()
    else:
        return ""

# This generates a list of xml samples of card titles
def getPics(url):
    result = requests.get(url)
    html = result.content
    soup = BeautifulSoup(html, "lxml")
    samples = soup.find_all("span", "cardTitle")
    return samples

# Gets the card name and multiverseID's from a sample and then saves them
def downloadPic(i, samples, set):

    expansion = 'data/images/'+set[:-1].replace('%20', '_')

    if not os.path.exists(expansion):
        os.makedirs(expansion)

    multiverseID = samples[i].a.attrs['href']
    multiverseID = multiverseID[34:]

    sampleName = samples[i].a.get_text()
    sampleName = sampleName.replace('/', '||')

    print("- "+sampleName)

    cardName = expansion+"/"+multiverseID+".jpg"
    URL = "http://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=%s&type=card" %multiverseID

    if not os.path.exists(cardName):
        urllib.urlretrieve(URL, cardName)

# This loops through each set in cardSets.txt


#with open('config/cardSets.txt') as sets:
with open('config/expansions.yaml', 'r') as sets:
    samples = []
    lastFirstPic = ""
    out = yaml.load(sets, Loader=yaml.FullLoader)

    for line in out['expansions']:
        n=0
        while(n<5):

            # This loops through the different pages page=0, page=1 etc.
            URL = "http://gatherer.wizards.com/Pages/Search/Default.aspx?page="+str(n)+"&set=%5B\""+urllib.quote(line)[:-1]+"\"%5D"

            # Check if the first pic is the same as the last first pic, if it is not download the images, or else exit the loop
            firstPic=getFirstPic(URL)
            if(firstPic!=lastFirstPic):
                print("\n-----------------------------------------------")
                print("Downloading images from " + line)
                print("-----------------------------------------------")
                samples = getPics(URL)
                for p in range(0,len(samples)):
                    downloadPic(p, samples, urllib.quote(line))
            else:
                n=6
            lastFirstPic=firstPic
            n+=1

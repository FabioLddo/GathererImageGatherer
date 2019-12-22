# Based on:
# https://gist.github.com/genekogan/ebd77196e4bf0705db51f86431099e57
# Special thanks to:

from selenium import webdriver
import json
import os
import urllib

# Below is the search term you want to search on google images (first try out manually, which term fetches you more relevant images)
searchterm = 'Snapcaster%20Mage%20innistrad'

counter = 0
ok_counter = 0
ko_counter = 0

url = "https://www.google.co.in/search?q="+searchterm+"&source=lnms&tbm=isch"
browser = webdriver.Chrome()
browser.get(url)
header = {'User-Agent': "Chrome/76.0.3809.36"}

if not os.path.exists(searchterm.replace('%20', '_')):
    os.mkdir(searchterm.replace('%20', '_'))

for _ in range(1):
    browser.execute_script("window.scrollBy(0,10000)")

for x in browser.find_elements_by_xpath('//div[contains(@class,"rg_meta")]'):

    counter = counter + 1
    #print("URL:", json.loads(x.get_attribute('innerHTML'))["ou"])
    img = json.loads(x.get_attribute('innerHTML'))["ou"]
    imgtype = json.loads(x.get_attribute('innerHTML'))["ity"]

    try:
        path = os.path.join(searchterm, searchterm + "_" + str(counter) + "." + imgtype)
        urllib.urlretrieve(img, path.replace('%20', '_'))
        ok_counter = ok_counter + 1

    except:
        ko_counter = ko_counter +1
        print("can't get img")

print("******************************************************************")
print("*", counter, "pictures detected to download                      *")
print("*", ok_counter, "pictures right downloaded                       *")
print("*", ko_counter, "pictures failed during download                 *")
print("******************************************************************")

browser.close()

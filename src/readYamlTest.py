
import yaml
import urllib

with open('config/expansions.yaml', 'r') as sets:
    out = yaml.load(sets, Loader=yaml.FullLoader)
    for expansions in out['expansions']:
        print urllib.quote(expansions) # Python 2
        # urllib.parse.quote(expansions) # Python 3

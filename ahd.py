#!/usr/bin/env python3

from argparse import ArgumentParser
from sys import exit
from urllib.request import urlopen, urlretrieve
from urllib.parse import quote_plus as qp
from re import findall, fullmatch
from base64 import b64decode as b64d
from pathlib import Path
from dataclasses import dataclass


__author__       = 'xdw/xnv'
__description__  = '[a]nime[h]eaven [d]ownloader you never asked for.'
__version__      = '0.1.0'
__project_link__ = 'http://github.com/xdw/ahd'


# GENERAL TODOs
# * Error handling (both in AnimeHeaven class and init.)
# * Logging (log everything to a file or stdout)
# * Debug mode, print logs verbosely
# * Full support of anime's attributes, like cover image and genres
# * Get rid of boilerplates


@dataclass
class Anime:
  ''' 
  Main anime object. 
  This class includes all attributes of an anime that AnimeHeaven provides.
  '''
  
  name: str
  episodes: int = 0
  path: Path = Path()
  url: str = ''
  genres: str = ''


class AnimeHeaven:
  ''' Main class to interact with AnimeHeaven. '''
  def __init__(self, debug=False):
    self.debug = debug
    self.link  = 'http://animeheaven.eu/'
  
  def search(self, name, include_dubbed=False):
    ''' 
    Search through AnimeHeaven. If include_dubbed option is True, search query 
    will crawl the dubbed ones as well. 
    '''
    
    # Search through AnimeHeaven. If status code of the request is anything but 200, exit.
    raw_search = urlopen(self.link + f'search.php?q={qp(name)}')
    if raw_search.getcode() != 200:
      exit(f'ERR AnimeHeaven returned code {raw_search.getcode()} during search.')
    
    # Decode HTML of search page from bytes to UTF-8 and then search through to find all the
    # anime names.
    search_html = raw_search.read().decode('utf8')
    anime_names = findall("<div class='conm'><a class='cona' href='i\.php\?a=(.*)'>", 
                          search_html)
    
    # If include_dubbed option is selected, search for dubbed ones too and add them to previous 
    # search result.
    if include_dubbed:
      anime_names += findall("<div class='condm'><a class='cona' href='i\.php\?a=(.*)'>", 
                             search_html)
    
    # Create Anime objects for each anime.
    results = [Anime(name, url=self.link + f'i.php?a={qp(name)}') for name in anime_names]

    return results
  
  #TODO: Support AnimeHeaven's changing-by-time variable names
  #TODO: Asynchronous downloading
  #TODO: Signal handling
  #TODO: Custom proxy and header support
  #TODO: Create the output directory if it doesn't exist
  #TODO: Make urlretrieve() more readable 
  def download(self, anime, episode, out=Path('animes/')):
    ''' Download given episode to out. '''

    # Make a request to episode page. If status code of the request is anything but 200, exit.
    raw_ep = urlopen(anime.url.replace('i.php', 'watch.php') + f'&e={episode}')
    if raw_ep.getcode() != 200:
      exit(f'ERR AnimeHeaven returned code {raw_ep.getcode()} during download.')
    
    # Decode HTML of episode page from bytes to UTF-8.
    ep_html = raw_ep.read().decode('utf8')

    # Check if there's "abuse" text in the page, this is for AnimeHeaven's abuse-protection 
    # system. We simply exit if there is.
    if 'abuse' in ep_html:
      exit("ERR Caught up to AnimeHeaven's abuse-protection. \
            Please wait at least 120 seconds to try again.")
    
    # First, search through the page to find episode's source URL. AnimeHeaven provides us this
    # under various variable names, but the format never changes. For now, this has to be 
    # statically typed in. And then we simply turn it to bytes from hexadecimal.
    #
    # After that, we reverse the AnimeHeaven's replace format and decode it with b64decode.
    # And of course to make things easier we decode bytes to UTF-8.
    dl_url = bytes.fromhex(
      findall('var lynt="(.*?)"', ep_html)[0].replace('\\x', '')
    )
    dl_url = b64d(dl_url.replace(
      b'|', str.encode(findall('lynt=lynt\.replace\(\/\\\|\/g,"(.*?)"\);', ep_html)[0])
    )).decode('utf8')
    
    # Download the episode to out/anime_name/episode.mp4. When a chunk downloaded, urlretrieve 
    # calls the function that we provided as 3rd argument. All it does is simply show how much
    # we downloaded so far in percentage.
    urlretrieve(
      dl_url, out / (anime.name + '/' + str(episode) + '.mp4'),
      lambda retrieved, chunk_size, total: print(
        f'INF Downloading episode {episode} of {anime.name} --- \
          {str(retrieved/(total/chunk_size)*100)[:4]}%',
        end='\r'
      )
    )

    print('\nINF Download completed!')

    return True
  
  
#TODO: If possible, make argument creations more readable
#TODO: Support 'l' keyword for last episode and None for all (this will make *episodes* 
# optional arg.)
if __name__ == '__main__':
  # Create parser and arguments.
  ap = ArgumentParser(
    description='[a]nime[h]eaven [d]ownloader',
    epilog='for more info on project visit git.io/fA4qr'
  )
  ap.add_argument(
    'anime', nargs='+', 
    help='name of the anime you want to download. (e.g. serial experiments lain)'
  )
  ap.add_argument(
    '-e', '--episodes', nargs='*', metavar='episode',
    help='episode(s) you want to download, by default, ahd downloads all of them. \
    (e.g. 1-5, 1-l, 1 2 3)'
  )
  ap.add_argument(
    '-o', '--out', nargs='*',
    help='output directory, it will be created if it does not exists - default is animes/'
  )
  ap.add_argument(
    '-id', '--include-dubbed', action='store_true',
    help='search for dubbed animes too, default is false'
  )
  
  # Parse the arguments, create AnimeHeaven object.
  args = ap.parse_args()
  ah   = AnimeHeaven()

  # Search for an anime.
  animes_found = ah.search(' '.join(args.anime), args.include_dubbed)
  
  # If multiple animes found, list all of them to the user and wait for input. Else, just 
  # continue from what we have.
  if len(animes_found) > 1:
    print(f'INF Found multiple animes named:', *args.anime, sep=' ')
    
    indexed_animes = {i: anime for i, anime in enumerate(animes_found)}
    
    for i, anime in indexed_animes.items():
      print(i, anime.name, sep='> ')
    
    while True:
      try:
        index = int(input('QUE Which one do you want to download? '))
        break
      except ValueError:
        print('INF You have to provide correct index of the anime you want to download.')
    
    anime = indexed_animes[index]
    
  else:
    anime = animes_found[0]
    
  # Parse different input formats for episodes.
  if args.episodes:
    if len(args.episodes) > 1:
      for ep in args.episodes:
        ah.download(anime, int(ep))
    
    elif len(args.episodes) == 1:
      for ep in map(int, args.episodes[0].split('-')):
        ah.download(anime, ep)
    
    
   
    







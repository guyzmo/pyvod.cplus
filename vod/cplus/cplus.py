"""\
Canal Plus Downloader

Downloads a movie from Canal Plus VOD

Usage:
  pycplus gui [<id>] [-t <target>] [--avconv <avconv>] [--verbose]
  pycplus fetch <id> [-t <target>] [--avconv <avconv>] [--verbose]
  pycplus get <id> [<key>...] [--verbose]
  pycplus show <id> [--verbose]
  pycplus list [<category>] [<channel>] [-l <limit>] [-s <sort>] [-i] [--verbose]
  pycplus search <query> [<category>] [<channel>] [-l <limit>] [-s <sort>] [-i] [--verbose]

Commands:
  gui                    Launch graphical user interface.
  get                    Get list of keys.
  get <key>              Get value for key.
  show                   Give summary for key.
  fetch                  Download the TV show.
  list                   List TV shows.
  search <query>         Search a TV show.

Options for `list` and `search` commands:
  <query>                Terms of the show to look up.
  <category>             Category to list. `help` or no value gives the list.
  <channel>              Channels to list. `help` or no value gives the list.
  -l --limit <limit>     Number of shows to output. [default: 100]
  -s --sort <sort>       Sort the output (alpha, date, relevance) [default: alpha]
  -i --image             Show thumbnail image URL for the show

Options for `get`, `show` and `fetch` commands:
  <id>                   URL or ID of the TV show
  -t --target <target>   Target directory to download the file to [default: ~/Downloads]
  --avconv <avconv>      Sets full path to avconv binary [default: /usr/bin/avconv]
  -V --verbose           Show more output.
  -h --help              Show this screen.

(c)2014 Bernard `Guyzmo` Pratz
Under the WTFPL <http://wtfpl.net>
"""

import sys
import json
import time
import textwrap
from lxml import etree

from vod.ui.cli import run
from vod.video import AVConvDownloader
from vod.vodservice import VodService
from vod.vodservice import VodServiceShow

### cplus

class CanalPlusShow(VodServiceShow):
    @property
    def id(self):
        return self['ID']

    @property
    def title(self):
        return self['INFOS']['TITRAGE']['TITRE']

    @property
    def image(self):
        return self['MEDIA']['IMAGES']['GRAND']

    def save(self, target_path="~/Downloads", callback=lambda p, t, d, s: print(p, t, d, s), avconv_path='/usr/bin/avconv', verbose=False):
        with self.downloader(target_path, avconv_path, verbose) as downloader:
            video_url = self['MEDIA']['VIDEOS']['HLS']
            title = self.title.replace("'","").replace(' ', '_').replace('/','')
            dest_file = "{}_{}.mkv".format(title, self.id)
            return downloader.save(dest_file, video_url, callback)

    def get_summary(self):
        yield _('Id'),          self['ID'],                             'short'
        yield _('Genre'),       self['RUBRIQUAGE']['CATEGORIE'],        'short'
        yield _('Broadcast'),   self['INFOS']['PUBLICATION']['DATE'],   'short'
        yield _('Length'),      self['DURATION'],                       'short'
        yield _('Channel'),     self['INFOS']['AUTEUR'],                'short'
        yield _('Website'),     self['URL'],                            'link'
        yield _('Picture'),     self['MEDIA']['IMAGES']['GRAND'],       'image'

    def get_crew(self):
        return []

    def get_synopsis(self):
        for line in textwrap.wrap(self['INFOS']['DESCRIPTION'], initial_indent="    "):
            yield "  {}".format(line)


class CanalPlusService(VodService):
    Show = CanalPlusShow
    video_url = "http://service.canal-plus.com/video/rest/getVideos/cplus/{show}?format=json"
    search_url = 'http://service.canal-plus.com/video/rest/search/cplus/{pat}?format=json'
    videos_url = 'http://service.canal-plus.com/video/rest/getMEAs/cplus/{cat}?format=json'
    categories_url = 'http://service.canal-plus.com/video/rest/initPlayer'

    categories = None
    channels = None

    def get_categories(self):
        if not self.categories:
            s = etree.XML(self.get(self.categories_url).text)
            self.categories = {}
            for sel in s.xpath("//THEMATIQUES/THEMATIQUE/SELECTIONS/SELECTION"):
                self.categories[sel.xpath("NOM/text()", encoding="utf-8")[0].replace(' ', '_')] = sel.xpath("ID/text()")[0]
        return self.categories.keys()

    def get_channels(self):
        return []

    def list(self, query=None, category=None, channel=None, limit=0, sort=None, page=0):
        r = []
        if category == "all": category=None
        if category:
            self.get_categories()
            cat = self.categories[category]
            r = json.loads(self.get(self.videos_url.format(cat=cat)).text)
        elif query:
            r = json.loads(self.get(self.search_url.format(pat=query)).text)
        else:
            r = json.loads(self.get(self.videos_url.format(cat="105")).text)

        return [self.Show(data) for data in r]

    def get_show(self, uri):
        if uri.startswith('http://') and 'canal' in uri:
            if 'vid=' in uri:
                show_id = uri.split('vid=')[-1]
            else:
                t = etree.HTML(self.get(uri).text)
                show_id = t.xpath('//player')[0].attrib['videoid']
        else:
            show_id = uri
        print(_('Get Data…'), end="\r", file=self.out)
        return self.Show(json.loads(self.get(self.video_url.format(show=show_id)).text),
                         self.out,
                         AVConvDownloader)


###################################################################################

def main():
    run(CanalPlusService, __doc__)

if __name__ == "__main__":
    run(CanalPlusService, __doc__)

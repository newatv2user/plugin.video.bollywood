import urllib, urllib2, re, sys, cookielib, os
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
from xbmcgui import ListItem
import CommonFunctions, StorageServer
import hosts

Addon = xbmcaddon.Addon()
Addonid = Addon.getAddonInfo('id')
settingsDir = Addon.getAddonInfo('profile')
settingsDir = xbmc.translatePath(settingsDir)

dbg = False # Set to false if you don't want debugging
dbglevel = 3 # Do NOT change from 3

common = CommonFunctions#.CommonFunctions()
common.dbg = True

# initialise cache object to speed up plugin operation
cache = StorageServer.StorageServer(Addonid, 12)

programs_thumb = os.path.join(Addon.getAddonInfo('path'), 'resources', 'media', 'programs.png')
topics_thumb = os.path.join(Addon.getAddonInfo('path'), 'resources', 'media', 'topics.png')
search_thumb = os.path.join(Addon.getAddonInfo('path'), 'resources', 'media', 'search.png')
next_thumb = os.path.join(Addon.getAddonInfo('path'), 'resources', 'media', 'next.png')

pluginUrl = sys.argv[0]
pluginhandle = int(sys.argv[1])

########################################################
## URLs
########################################################
SITE = 'http://www.sominaltvfilms.com'
SEARCHURL = '/search?q=%s'
TRAILERS = '/search/label/Trailers'

########################################################
## Modes
########################################################
M_DO_NOTHING = 0
M_Browse = 1
M_Trailers = 2
M_Search = 3
M_GET_VIDEO_LINKS = 4
M_Categories = 7

##################
## Class for items
##################
class MediaItem:
    def __init__(self):
        self.ListItem = ListItem()
        self.Image = ''
        self.Url = ''
        self.Isfolder = False
        self.Mode = ''
        self.Label = ''
        
## Get URL
def getURL(url):
    print 'getURL :: url = ' + url
    cj = cookielib.LWPCookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-Agent', 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2;)')]
    usock = opener.open(url)
    response = usock.read()
    usock.close()
    return unicode(response, 'utf-8', 'ignore')

########################################################
## Mode = None
## Build the main directory
########################################################
def BuildMainDirectory():
    Browse('')

###########################################################
## Mode == M_Categories
## Browse all documentaries
###########################################################
def Categories():
    contents = cache.cacheFunction(getURL, SITE)
    menuBar = common.parseDOM(contents, 'ul', {'id': 'menubar'})
    if not menuBar:
        return
    menuBar = menuBar[0]
    #menuBar = menuBar.replace('<li>', '<li/>')
    catDOM = common.parseDOM(menuBar, 'li')
    #print 'Debug Info - catDOM length: ' + str(len(catDOM))
    MediaItems = []
    for dCat in catDOM:
        if dCat is None or dCat == '':
            continue
        #print 'Debug Info: ' + dCat
        Title = common.stripTags(dCat)
        Title = common.replaceHTMLCodes(Title)
        #print 'Debug Info: ' + Title
        if Title == 'Requests':
            continue

        href = common.parseDOM(dCat, "a", ret="href")
        '''if len(href) > 1:
            continue
        if href[0].find('films') == -1:
            continue'''
        Url = href[0]
        print 'Debug Info: ' + Url
        if Url == '#':
            subCats = common.parseDOM(dCat, 'li')
            for cat in subCats:
                Title = common.stripTags(cat)
                Title = common.replaceHTMLCodes(Title)
                #print 'Debug Info 2: ' + Title
                href = common.parseDOM(cat, "a", ret="href")
                if not href:
                    continue
                Url = href[0]
                #print 'Debug Info 2: ' + Url
                Mediaitem = MediaItem()
                Mediaitem.ListItem.setLabel(Title)
                Mediaitem.Label = Title
                mode = M_Browse
                Mediaitem.Url = pluginUrl + "?url=" + urllib.quote_plus(Url) + "&mode=" + str(mode)
                Mediaitem.Isfolder = True
                MediaItems.append(Mediaitem)
        else:
            Mediaitem = MediaItem()
            Mediaitem.ListItem.setLabel(Title)
            Mediaitem.Label = Title
            mode = M_Browse
            Mediaitem.Url = pluginUrl + "?url=" + urllib.quote_plus(Url) + "&mode=" + str(mode)
            Mediaitem.Isfolder = True
            MediaItems.append(Mediaitem)
        
    SortedItems = sorted(Unique(MediaItems, lambda x: x.Url), key=lambda item: item.Label)    
    addDir(SortedItems)
    xbmcplugin.endOfDirectory(pluginhandle)

###########################################################
## Mode == M_Browse
## Browse documentaries. All or by categories
###########################################################   
def Browse(url):
    #print 'Ready to browse now.'
    # set content type so library shows more views and info
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    if url == '':
        url = SITE
    contents = cache.cacheFunction(getURL, url)
        
    itemsDOM = common.parseDOM(contents, "div", attrs={ "id": "summary[\d]+"})
    itemIDS = common.parseDOM(contents, 'div', {'id': 'summary[\d]+'}, ret='id')
    MediaItems = []
    count = 0
    for item in itemsDOM:
        Mediaitem = MediaItem()

        Plot = common.stripTags(item)
        Plot = common.replaceHTMLCodes(Plot)        
                    
        Image = common.parseDOM(item, "img", ret="src")
        try:
            Mediaitem.Image = Image[0]
        except:
            Mediaitem.Image = ''
        
        Patt = '"%s","(.+?)","(.+?)"' % itemIDS[count]
        Match = re.compile(Patt).findall(contents)
        if not Match:
            count += 1
            continue
        Title, Url = Match[0]
        Mediaitem.ListItem.setLabel(Title)
        Mediaitem.ListItem.setInfo('video', { 'Title': Title, 'Plot': Plot})    
        
        mode = M_GET_VIDEO_LINKS
        Mediaitem.Url = pluginUrl + "?url=" + urllib.quote_plus(Url) + "&mode=" + str(mode) + "&name=" + urllib.quote_plus(Title)
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        
        MediaItems.append(Mediaitem)
        count += 1
        
    nextPage = common.parseDOM(contents, "a", attrs={ "class": "blog-pager-older-link"}, ret="href")
    for url in nextPage:
        Mediaitem = MediaItem()
        Mediaitem.Image = next_thumb
        Mediaitem.ListItem.setLabel('Next')
        Mediaitem.Isfolder = True
        Mediaitem.Mode = M_Browse
        Mediaitem.Url = pluginUrl + "?url=" + urllib.quote_plus(url) + "&mode=" + str(Mediaitem.Mode)
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        MediaItems.append(Mediaitem)
        
    # Other Menu Items
    bottom = [
        (Addon.getLocalizedString(30014), topics_thumb, M_Categories),
        (Addon.getLocalizedString(30016), topics_thumb, M_Trailers),
        (Addon.getLocalizedString(30015), search_thumb, M_Search)
        ]
    for name, thumbnailImage, mode in bottom:
        Mediaitem = MediaItem()
        Mediaitem.Image = thumbnailImage
        Mediaitem.ListItem.setLabel(name)
        Mediaitem.Isfolder = True
        Mediaitem.Mode = mode
        Mediaitem.Url = pluginUrl + "?mode=" + str(Mediaitem.Mode)
        Mediaitem.ListItem.setThumbnailImage(Mediaitem.Image)
        MediaItems.append(Mediaitem)
        
    addDir(MediaItems)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    SetViewMode()

###########################################################
## Mode == M_GET_VIDEO_LINKS
## Try to get a list of playable items and play it.
###########################################################
def Playlist(url):
    #print 'Fetching links from ' + url
    Matches = None
    Patterns = [ 'href="http://adf.ly/\d{1,}/([^"]+)">Full Movie \(Click Here\)',
                'href="http://adf.ly/\d{1,}/([^"]+)".+?>',
                'href="([^"]+)">Full Movie \(Click Here\)',
                'href="([^"]+)"[^P]+Part ' ]
    try:
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        contents = cache.cacheFunction(getURL, url)
    
        itemsDOM = common.parseDOM(contents, "div", attrs={ "class": "entry"})
        #itemsDOM = common.parseDOM(contents, "div", attrs = { "style": "text-align: center;"})
        entry = itemsDOM[1]
        #print entry
        Matches = hosts.resolve(entry)
        
        if Matches == None or len(Matches) == 0:
            for Pattern in Patterns:
                adClick = re.compile(Pattern).findall(entry)
                if len(adClick) > 0:
                    for url1 in adClick:
                        if url1 is not None and url1 != '':
                            contents2 = cache.cacheFunction(getURL, url1)
                        if contents2 is not None:
                            MatchesI = hosts.resolve(contents2)
                            if MatchesI is not None:
                                Matches.extend(MatchesI)
                if len(Matches) > 0:
                    break
                
    except:
        print 'Exception occurred.'
        pass
    finally:
        xbmc.executebuiltin("Dialog.Close(busydialog)")

    if Matches == None or len(Matches) == 0:
        xbmcplugin.setResolvedUrl(pluginhandle, False,
                                  xbmcgui.ListItem())
        dialog = xbmcgui.Dialog()
        ok = dialog.ok('Nothing to play', 'A playable url could not be found.')
        return
    if Matches[0].find('playlist') > 0:
        #print Matches[0]
        #listitem = xbmcgui.ListItem(path=Matches[0])
        #listitem.setProperty("IsPlayable", "true")
        #return xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
        return xbmc.executebuiltin("xbmc.PlayMedia(" + Matches[0] + ")")
        #return xbmcplugin.setResolvedUrl(pluginhandle, True, 
        #                          xbmcgui.ListItem(path=Matches[0]))
        
    playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playList.clear()
    for PlayItem in Matches:
        #print PlayItem
        listitem = xbmcgui.ListItem('Video')
        listitem.setInfo(type="video", infoLabels={ "Title": name })
        listitem.setProperty("IsPlayable", "true")
        playList.add(url=PlayItem, listitem=listitem)
    xbmcPlayer = xbmc.Player()
    xbmcPlayer.play(playList)

# Set View Mode selected in the setting
def SetViewMode():
    try:
        # if (xbmc.getSkinDir() == "skin.confluence"):
        if Addon.getSetting('view_mode') == "1": # List
            xbmc.executebuiltin('Container.SetViewMode(502)')
        if Addon.getSetting('view_mode') == "2": # Big List
            xbmc.executebuiltin('Container.SetViewMode(51)')
        if Addon.getSetting('view_mode') == "3": # Thumbnails
            xbmc.executebuiltin('Container.SetViewMode(500)')
        if Addon.getSetting('view_mode') == "4": # Poster Wrap
            xbmc.executebuiltin('Container.SetViewMode(501)')
        if Addon.getSetting('view_mode') == "5": # Fanart
            xbmc.executebuiltin('Container.SetViewMode(508)')
        if Addon.getSetting('view_mode') == "6":  # Media info
            xbmc.executebuiltin('Container.SetViewMode(504)')
        if Addon.getSetting('view_mode') == "7": # Media info 2
            xbmc.executebuiltin('Container.SetViewMode(503)')
            
        if Addon.getSetting('view_mode') == "0": # Default Media Info for Quartz
            xbmc.executebuiltin('Container.SetViewMode(52)')
    except:
        print "SetViewMode Failed: " + Addon.getSetting('view_mode')
        print "Skin: " + xbmc.getSkinDir()

# Search documentaries
def SEARCH(url):
        # set content type so library shows more views and info
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    
        if url is None or url == '':
            keyb = xbmc.Keyboard('', 'Search Sominaltvtheater')
            keyb.doModal()
            if (keyb.isConfirmed() == False):
                return
            search = keyb.getText()
            if search is None or search == '':
                return
            search = search.replace(" ", "+")
            #encSrc = urllib.quote(search)
            url = SITE + SEARCHURL % search
        Browse(url)

## Get Parameters
def get_params():
        param = []
        paramstring = sys.argv[2]
        if len(paramstring) >= 2:
                params = sys.argv[2]
                cleanedparams = params.replace('?', '')
                if (params[len(params) - 1] == '/'):
                        params = params[0:len(params) - 2]
                pairsofparams = cleanedparams.split('&')
                param = {}
                for i in range(len(pairsofparams)):
                        splitparams = {}
                        splitparams = pairsofparams[i].split('=')
                        if (len(splitparams)) == 2:
                                param[splitparams[0]] = splitparams[1]
        return param

def addDir(Listitems):
    if Listitems is None:
        return
    Items = []
    for Listitem in Listitems:
        Item = Listitem.Url, Listitem.ListItem, Listitem.Isfolder
        Items.append(Item)
    handle = pluginhandle
    xbmcplugin.addDirectoryItems(handle, Items)

def Unique(seq, idfun=None):
    ''' Return a unique list
        Source: http://www.peterbe.com/plog/uniqifiers-benchmark
    '''
    # order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        #print 'wtf: ' + item.Url
        marker = idfun(item)
        # in old Python versions:
        # if seen.has_key(marker)
        # but in new ones:
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result
                    
params = get_params()
url = None
name = None
mode = None
titles = None
try:
        url = urllib.unquote_plus(params["url"])
except:
        pass
try:
        name = urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode = int(params["mode"])
except:
        pass
try:
        titles = urllib.unquote_plus(params["titles"])
except:
        pass

xbmc.log("Mode: " + str(mode))
#print "URL: " + str(url)
#print "Name: " + str(name)
#print "Title: " + str(titles)

if mode == None: #or url == None or len(url) < 1:
        #print "Top Directory"
        BuildMainDirectory()
elif mode == M_DO_NOTHING:
    print 'Doing Nothing'
elif mode == M_Categories:
    #print 'Categories'
    Categories()
elif mode == M_Browse:
    #print 'Browse'
    Browse(url)
elif mode == M_Trailers:
    #print 'Trailers'
    Browse(SITE + TRAILERS)
elif mode == M_Search:
        #print "SEARCH  :" + url
        SEARCH(url)
elif mode == M_GET_VIDEO_LINKS:
    #print 'Trying to get the links and play it.'
    Playlist(url)

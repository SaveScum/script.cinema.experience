import os, sys, time, re, urllib, traceback, datetime, tmdbsimple.base
import tmdbsimple as tmdb

from random import shuffle, random
from xml.sax.saxutils import unescape
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

import xbmc, xbmcvfs

__script__               = sys.modules[ "__main__" ].__script__
__scriptID__             = sys.modules[ "__main__" ].__scriptID__
trailer_settings         = sys.modules[ "__main__" ].trailer_settings
BASE_CACHE_PATH          = sys.modules[ "__main__" ].BASE_CACHE_PATH
BASE_RESOURCE_PATH       = sys.modules[ "__main__" ].BASE_RESOURCE_PATH
BASE_CURRENT_SOURCE_PATH = sys.modules[ "__main__" ].BASE_CURRENT_SOURCE_PATH
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from ce_playlist import _get_thumbnail, _get_trailer_thumbnail
import utils

class Main:
    def __init__( self, equivalent_mpaa=None, mpaa=None, genre=None, settings=None, movie=None ):
        utils.log( "Initializing TheMovieDB trailer scraper", xbmc.LOGNOTICE )
        #TODO: Get my own API key instead of cribbing from Kodi
        tmdb.API_KEY = '57983e31fb435df4df77afb854740ea9'
        self.settings = settings
        self.watched_path = os.path.join( BASE_CURRENT_SOURCE_PATH, self.settings[ "trailer_scraper" ] + "_watched.txt" )
        utils.log(simplejson.dumps(self.settings))
        if settings['trailer_limit_mpaa'] :
            self.mpaa = mpaa
        elif settings['trailer_rating'] == '--' :
            self.mpaa = settings['trailer_rating']
        else:
            self.mpaa = ""
            
        self.rating_query = self.mpaa
            
        self.genres = []
        if not settings['trailer_limit_genre'] :
            self.genres = genre.split( " / " )
        
        self.genre_ids = []
        for g in (tmdb.Genres().list()['genres']): 
            if g['name'] in self.genres and len(self.genres) < 2:
                self.genre_ids.append( g['id'] )
                
        self.genre_query = "|".join(str(x) for x in self.genre_ids)
                
        self.movie = movie
        #  initialize trailer list
        self.trailers = []

    def fetch_trailers( self ):        
        # get watched list
        self._get_watched()
                
        result_page = 0
        movies_with_trailers = []
        
        while True:
            result_page += 1
            utils.log("Fetching movies")            
            search_params = { 'page' : result_page,
                        'with_genres': self.genre_query,
                        'certification.lte': self.mpaa,
                        'certification.gte': self.mpaa}
            utils.log("Searching with:  %s " % urllib.urlencode(search_params))
            moviedb_results = self._get_batch_of_movies(search_params)
            utils.log("Got %i results" % moviedb_results['total_results'])
            utils.log(simplejson.dumps( moviedb_results))
           
            
            if moviedb_results['total_results'] == 0:
                break            
        
            movie_ids = []
            for m in moviedb_results['results']:
                movie_ids.append(m['id'])
            
            for m_id in movie_ids:            
                #desired number of trailers reached
                if len(movies_with_trailers) >= self.settings[ "trailer_count" ]:
                    break
                if m_id in self.watched and self.settings[ "trailer_unwatched_only" ]:
                    continue
                this_movie = tmdb.Movies(m_id)
                movie_info = this_movie.info()
                for v in this_movie.videos()['results']:
                    if v['site'] == "YouTube" and v['type'] == "Trailer":
                        movie_info['trailer'] = v
                        break
                        
                if movie_info.has_key('trailer'):
                    movies_with_trailers.append(movie_info)        
                    
                    
            #desired number of trailers reached
            if len(movies_with_trailers) >= self.settings[ "trailer_count" ]:
                break
                
            #tmdbsimple won't go beyond page 1000
            #TODO: how long would it take to scrape through 1000 pages of results? consider lowering this
            if result_page == moviedb_results['total_pages'] or result_page > 999:
                #clear the watched list, since it's probably time to start over from the beginning
                #self._reset_watched()
                break
                    
        for m in movies_with_trailers:
            video_url = "plugin://plugin.video.youtube/play/?video_id=%s" % m['trailer']['key']
            utils.log("Adding trailer %s" % video_url, xbmc.LOGNOTICE)
            this_trailer = ( '', # id
                             '', # title
                             video_url, # trailer
                             '', # thumb
                             '', # plot
                             '', # runtime
                             '', # mpaa
                             '', # release date
                             '', # studio
                             '', # genre
                             '', # writer
                             '', # director
                            )
            self.trailers += [ this_trailer ]
            if m['id'] not in self.watched:
                self.watched.append(m['id'])
        
        self._save_watched()
        #return trailers
        utils.log(simplejson.dumps(self.trailers))
        return self.trailers
        
        
    def _get_batch_of_movies( self, params):
        return tmdb.Discover().movie(**params)
        

    def _get_watched( self ):
        self.watched = utils.load_saved_list( self.watched_path, "Trailer Watched List" )

    def _reset_watched( self ):
        utils.log( "Resetting Watched List", xbmc.LOGNOTICE )
        if xbmcvfs.exists( self.watched_path ):
            xbmcvfs.delete( self.watched_path )
            self.watched = []

    def _save_watched( self ):
        utils.save_list( self.watched_path, self.watched, "Watched Trailers" )


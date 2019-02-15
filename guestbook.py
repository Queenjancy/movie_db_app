#!/usr/bin/env python

# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START imports]
import os
import urllib

from google.appengine.api import users
from google.appengine.api import search
from google.appengine.ext import ndb

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

DEFAULT_GENRE = 'animation'


# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent. However, the write rate should be limited to
# ~1/second.

def movie_key(movie_genre=DEFAULT_GENRE):
    """Constructs a Datastore key for a Guestbook entity.

    We use movie_genre as the key.
    """
    return ndb.Key('movie_genre', movie_genre)


# [START greeting]
#class Author(ndb.Model):
#   """Sub model for representing an author."""
#   identity = ndb.StringProperty(indexed=False)
#   email = ndb.StringProperty(indexed=False)

class MovieInfo(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    title = ndb.StringProperty(indexed=False)
    director = ndb.StringProperty(indexed=False)
    main_actor1 = ndb.StringProperty(indexed=False)
    main_actor2 = ndb.StringProperty(indexed=False)
    release_year = ndb.StringProperty(indexed=False)
    duration = ndb.StringProperty(indexed=False)
# [END greeting]


# [START main page]
class MainPage(webapp2.RequestHandler):

    def get(self): 
        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = {}
        self.response.write(template.render(template_values))
# [END main page]


# [START display]
class Display(webapp2.RequestHandler):

    def get(self):
        movie_genre = self.request.get('movie_genre',
                                          DEFAULT_GENRE)
        movie_query = MovieInfo.query(
            ancestor=movie_key(movie_genre))
        movies = movie_query.fetch()

        template_values = {
            'movie_genre': movie_genre,
            'movies': movies
        }

        template = JINJA_ENVIRONMENT.get_template('display.html')
        self.response.write(template.render(template_values))
# [END display]


def tokenize(word):
    a = []
    for j in range(1, len(word) + 1):
        for i in range(len(word) - j + 1):
            a.append(word[i: i + j])
    return a


# [START info]
class Info(webapp2.RequestHandler):

    def get(self):
        template = JINJA_ENVIRONMENT.get_template('info.html')
        genre_name = self.request.get('movie_genre', DEFAULT_GENRE)
        template_value = {'movie_genre': genre_name}
        self.response.write(template.render(template_value))



    def post(self):

        # if the parent 'genre' field is not switched to another one, use DEFAULT_GENRE
        genre_name = self.request.get('movie_genre', DEFAULT_GENRE)

        movie_info = MovieInfo(parent=movie_key(genre_name))
        movie_info.title = self.request.get('title');
        movie_info.director = self.request.get('director');
        movie_info.main_actor1 = self.request.get('main_actor1');
        movie_info.main_actor2 = self.request.get('main_actor2');
        movie_info.release_year = self.request.get('release_year');
        movie_info.duration = self.request.get('duration');

        raise_error = False
        if len(movie_info.title) is 0 or len(movie_info.director) is 0 or len(movie_info.release_year) is 0 or len(movie_info.duration) is 0:
            raise_error = True
            template_value = {
                'raise_error': raise_error
            }
            template = JINJA_ENVIRONMENT.get_template('info.html')
            self.response.write(template.render(template_value))
            return

        movie_info.put();

        # create search index for MovieInfo
        # add content to the index via its document, and add title, director main_actor and release year as fields
        title_tokens = ','.join(tokenize(movie_info.title.lower()))
        director_tokens = ','.join(tokenize(movie_info.director.lower()))
        actor_tokens = ','.join(tokenize(movie_info.main_actor1.lower()) + tokenize(movie_info.main_actor2.lower()))
        complete_info = movie_info.title + ', ' + movie_info.director + ', ' + movie_info.main_actor1 + ', ' + movie_info.main_actor2 + ', ' + movie_info.release_year + ', ' + movie_info.duration
        item_index = search.Index(name=genre_name)
        item_fields = [
            search.TextField(name='title', value=title_tokens),
            search.TextField(name='director',value=director_tokens),
            search.TextField(name='main_actor', value=actor_tokens),
            search.TextField(name='release_year',value=movie_info.release_year),
            search.TextField(name='complete_info', value=complete_info)
        ]
        document = search.Document(fields=item_fields)
        search.Index(name=genre_name).put(document)

        # redirect to main page after entering a new movie
        self.redirect('/')
# [END info]



# [START movie search]
class MovieSearch(webapp2.RequestHandler):

    def get(self):
        genre_name = self.request.get('movie_genre', DEFAULT_GENRE)
        template = JINJA_ENVIRONMENT.get_template('search.html')
        template_value = {
            'movie_genre': genre_name,
        }
        self.response.write(template.render(template_value))


    def post(self):
        genre_name = self.request.get('movie_genre', DEFAULT_GENRE)
        title = self.request.get('title').lower()
        director = self.request.get('director').lower()
        main_actor = self.request.get('actor').lower()
        release_year = self.request.get('release_year').lower()

        raise_error = False
        if len(title) is 0 and len(director) is 0 and len(main_actor) is 0 and len(release_year) is 0:
            raise_error = True
            template_value = {
                'raise_error': raise_error
            }
            template = JINJA_ENVIRONMENT.get_template('search.html')
            self.response.write(template.render(template_value))
            return

        # use the GAE search API to query multiple fields
        # hwo to do the search within a specified ancestor?
        query_string = ""
        if len(title) > 0:
            query_string += "title:"
            query_string += title.lower()
        if len(director) > 0:
            query_string += " director:"
            query_string += director.lower()
        if len(main_actor) > 0:
            query_string += " main_actor:"
            query_string += main_actor.lower()
        if len(release_year) > 0:
            query_string += " release_year:"
            query_string += release_year

        index = search.Index(name=genre_name)
        search_result = index.search(query_string)

        # display the search results
        template_values = {
            'movie_genre': genre_name,
            'search_result': search_result
        }
        template = JINJA_ENVIRONMENT.get_template('search.html')
        self.response.write(template.render(template_values))
        #self.response.write(query_string)
# [END movie search]




# [START app]
# defining which script handles request for givan URLs
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/display', Display),
    ('/info', Info),
    ('/search', MovieSearch)
], debug=True)
# [END app]

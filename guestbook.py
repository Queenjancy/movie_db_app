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
import datetime

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
    rent_price = ndb.StringProperty(indexed=False);
    buy_price = ndb.StringProperty(indexed=False);
# [END greeting]


# [START purchase]
class Purchase(ndb.Model):
    item = ndb.StringProperty(indexed=False)
    purchase_price = ndb.StringProperty(indexed=False)

    def __eq__(self, other):
        return self.item == other.item
# [END purchase]


# [START shopping cart]
class ShoppingCart(ndb.Model):
    '''Model for shpping cart'''
    id = ndb.StringProperty()
    purchases = ndb.StructuredProperty(Purchase, repeated=True)
    total_cost = ndb.FloatProperty(indexed=False)
# [END shoppinf cart]


# [START check out record]
class CheckOutRecord(ndb.Model):
    id = ndb.StringProperty
    purchases = ndb.StructuredProperty(Purchase, repeated=True)
    time = ndb.DateTimeProperty()
# [END check out record]


# [START main page]
class MainPage(webapp2.RequestHandler):

    def get(self): 
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template = JINJA_ENVIRONMENT.get_template('index.html')
        template_values = {
            'user': user,
            'url': url,
            'url_linktext': url_linktext
        }
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


    def post(self):
        # get movie and movie price
        movie_title = self.request.get('movie')
        movie_price = self.request.get('purchase_price')

        user = users.get_current_user()
        if user is None:
            return
        # if the user exists in database, retrieve its shopping cart; otherwise create a new cart
        cart = ndb.Key(ShoppingCart, str(user.email)).get()
        if cart is None: 
            cart = ShoppingCart(id=str(user.email), purchases=[], total_cost=0)
            cart.key = ndb.Key(ShoppingCart, str(user.email))
        # if movie is already purchased, do not allow it to be purchased twice
        matching_list = [x for x in cart.purchases if x.item == movie_title]
        if not matching_list:
            title_modified = movie_title.replace(" ", "-")
            print(title_modified)
            cart.purchases.append(Purchase(item=title_modified, purchase_price=movie_price))
            print(movie_price)
            cart.total_cost = cart.total_cost + float(movie_price)
            cart.put()
        self.redirect('/')


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
        movie_info.title = self.request.get('title').replace(" ", "_");
        movie_info.director = self.request.get('director');
        movie_info.main_actor1 = self.request.get('main_actor1');
        movie_info.main_actor2 = self.request.get('main_actor2');
        movie_info.release_year = self.request.get('release_year');
        movie_info.duration = self.request.get('duration');
        movie_info.rent_price = self.request.get('rent_price');
        movie_info.buy_price = self.request.get('buy_price');


        raise_error = False
        if len(movie_info.title) is 0 or len(movie_info.director) is 0 or len(movie_info.release_year) is 0 or len(movie_info.duration) is 0 or len(movie_info.rent_price) is 0 or len(movie_info.buy_price) is 0:
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
        complete_info = movie_info.title + ', ' + movie_info.director + ', ' + movie_info.main_actor1 + ', ' + movie_info.main_actor2 + ', ' + movie_info.release_year + ', ' + movie_info.duration + ', rent: $' + movie_info.rent_price + ", buy: $" + movie_info.buy_price
        item_index = search.Index(name=genre_name)
        item_fields = [
            search.TextField(name='title', value=title_tokens),
            search.TextField(name='director',value=director_tokens),
            search.TextField(name='main_actor', value=actor_tokens),
            search.TextField(name='release_year',value=movie_info.release_year),
            search.TextField(name='complete_info', value=complete_info),
            search.TextField(name='rent_price', value=movie_info.rent_price),
            search.TextField(name='buy_price', value=movie_info.buy_price),
            search.TextField(name='full_title', value=movie_info.title)]
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




# [START check cart]
class CheckCart(webapp2.RequestHandler):

    def get(self):
        user = users.get_current_user()
        if user is None:
            return
        # if the user exists in database, retrieve its shopping cart; else create a new cart
        cart = ndb.Key(ShoppingCart, str(user.email)).get()
        if cart is None: 
            cart = ShoppingCart(id=str(user.email), purchases=[], total_cost=0)
            cart.key = ndb.Key(ShoppingCart, str(user.email))
        template = JINJA_ENVIRONMENT.get_template('/cart.html')
        template_value = {'cart': cart}
        self.response.write(template.render(template_value))


    def post(self):
        user = users.get_current_user()
        email = str(user.email)
        cart = ndb.Key(ShoppingCart, email).get()
        completed = False

        if self.request.get("checkout"):
            dt = datetime.datetime.now()
            record = CheckOutRecord(id=email, purchases=cart.purchases, time=dt)
            record.key = ndb.Key(CheckOutRecord, email)
            record.put()
            cart.purchases = []
            cart.total_cost = 0
            cart.put()
            completed = True

        movie = self.request.get('movie')
        if movie:
            for purchase in cart.purchases: 
                if purchase.item == movie: 
                    cart.purchases.remove(purchase)
                    cart.total_cost = cart.total_cost - float(purchase.purchase_price)
            cart.put()

        template = JINJA_ENVIRONMENT.get_template('cart.html')
        template_values = {
            'cart': cart,
            'completed': completed
        }
        self.response.write(template.render(template_values))

    '''
    def delete(self):
        movieToDelete = self.request.get('movie')
        user = users.get_current_user
        cart = ndb.Key(ShoppingCart, str(user.email)).get()
        cart.purchases.remove(movieToDelete)
        cart.put()

        template = JINJA_ENVIRONMENT.get_template('cart.html')
        template_values = {
            'cart': cart
        }
        self.response.write(template.render(template_values))
    '''


# [START app]
# defining which script handles request for givan URLs
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/display', Display),
    ('/info', Info),
    ('/search', MovieSearch),
    ('/cart', CheckCart)
], debug=True)
# [END app]

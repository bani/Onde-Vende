# -*- coding: utf-8 -*-
# Copyright 2010 Vanessa Sabino
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

__author__ = "Vanessa Sabino"

import oauth
import keys
import urllib
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from google.appengine.ext import db

try:
    import simplejson
except ImportError:
    try:
        import json as simplejson
    except ImportError:
        try:
            from django.utils import simplejson
        except:
            raise Exception("SimpleJson nao encontrado")

class LastTweet(db.Model):
    tweetId = db.IntegerProperty()
    

class MainHandler(webapp.RequestHandler):
        
    def get(self):
        callback_url = "%s/verify" % self.request.host_url
        client = oauth.TwitterClient(keys.application_key, keys.application_secret, 
            callback_url)
        
        lastTweet = db.GqlQuery("SELECT * FROM LastTweet").fetch(1)[0]
        params = {}
        params["since_id"] = lastTweet.tweetId
            
        mentions_url = "http://api.twitter.com/statuses/mentions.json"
        result = client.make_request(url=mentions_url, token=keys.ondevende['user_token'], 
        secret=keys.ondevende['user_secret'], additional_params=params, method=urlfetch.GET)
        
        statuses = simplejson.loads(result.content)
 
        for status in statuses:
            id = status["id"]
            user = "@"+status["user"]["screen_name"]+" "
            msg = self.getBestPrice(status["text"])
            if len(msg) > 1:
                self.postTweet(id, user + msg)
            
        if statuses:
            lastTweet.tweetId = statuses[0]["id"]
            lastTweet.put()
       
    def getBestPrice(self, status):
        logging.info("Processando: %s", status)
        tweet = "Desculpe, não consegui encontrar o produto"
        if status.find("@ondevende") == 0:
            status = status.replace("@ondevende", "").strip()
        else:
            return ""
        
        keyword = urllib.quote(status)
        buscapeUrl = "http://sandbox.buscape.com/service/findOfferList/%s/?keyword=%s&sort=price&format=json" % (keys.buscape_id, keyword)

        try:
            result = urlfetch.fetch(url=buscapeUrl)
            buscapeData = simplejson.loads(result.content.decode("utf-8"))
            
            price = buscapeData["offer"][0]["offer"]["price"]["value"].replace(".",",")
            store = buscapeData["offer"][0]["offer"]["seller"]["sellername"]
            link = buscapeData["offer"][0]["offer"]["links"][0]["link"]["url"]
           
            bitlyUrl = "http://api.bit.ly/v3/shorten?login=%s&apiKey=%s&longUrl=%s&format=txt" % (keys.bitly_login, keys.bitly_key, urllib.quote(link.strip()))
            shortenedLink = urlfetch.fetch(url=bitlyUrl).content
            
            tweet = "em %s por R$%s - %s" % (store, price, shortenedLink)
        except:
            logging.error("Erro ao processar a URL %s" % buscapeUrl)
        
        return tweet
    
    def postTweet(self, id, tweet):
        callback_url = "%s/verify" % self.request.host_url
        client = oauth.TwitterClient(keys.application_key, keys.application_secret, 
            callback_url)

        update_url = "http://twitter.com/statuses/update.xml"
        client.make_request(url=update_url, token=keys.ondevende['user_token'], 
        secret=keys.ondevende['user_secret'], additional_params={'in_reply_to_status_id': id,'status':tweet}, method=urlfetch.POST)


application = webapp.WSGIApplication(
                                     [('/buscape', MainHandler)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
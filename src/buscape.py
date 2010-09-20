# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# This is an sample AppEngine application that shows how to 1) log in a user
# using the Twitter OAuth API and 2) extract their timeline.
#
# INSTRUCTIONS: 
#
# 1. Set up a new AppEngine application using this file, let's say on port 
# 8080. Rename this file to main.py, or alternatively modify your app.yaml 
# file.)
# 2. Fill in the application ("consumer") key and secret lines below.
# 3. Visit http://localhost:8080 and click the "login" link to be redirected
# to Twitter.com.
# 4. Once verified, you'll be redirected back to your app on localhost and
# you'll see some of your Twitter user info printed in the browser.
# 5. Copy and paste the token and secret info into this file, replacing the 
# default values for user_token and user_secret. You'll need the user's token 
# & secret info to interact with the Twitter API on their behalf from now on.
# 6. Finally, visit http://localhost:8080/timeline to see your twitter 
# timeline.
#

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
        if lastTweet:
            params["since_id"] = lastTweet.tweetId
            
        mentions_url = "http://api.twitter.com/statuses/mentions.json"
        result = client.make_request(url=mentions_url, token=keys.ondevende['user_token'], 
        secret=keys.ondevende['user_secret'], additional_params=params, method=urlfetch.GET)
        
        statuses = simplejson.loads(result.content)
        if statuses:
            if not lastTweet:
                lastTweet = LastTweet() 
 
        for status in statuses:
            id = status["id"]
            user = "@"+status["user"]["screen_name"]+" "
            msg = self.getBestPrice(status["text"])
            self.postTweet(id, user + msg)
            
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
            buscapeData = simplejson.loads(result.content)
            
            price = buscapeData["offer"][0]["offer"]["price"]["value"].replace(".",",")
            store = buscapeData["offer"][0]["offer"]["seller"]["sellername"]
            
            tweet = "Compre em %s por R$%s" % (store, price)
        except:
            logging.error("Erro ao processar a URL %s" % buscapeUrl)
        
        return tweet
    
    def postTweet(self, id, tweet):
        if len(tweet) > 1:
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
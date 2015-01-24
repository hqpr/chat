import urlparse
import uuid

import os
import json

import tornado.web
import tornado.ioloop
import tornado.websocket

from pymongo import MongoClient

client = MongoClient()
db = client.chat
users = db.users

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        db = self.application.db
        messages = db.chat.find()

        # if not self.current_user:
        #     self.redirect("/login")
        #     return
        self.render('index.html', messages=messages)



class WebSocket(tornado.websocket.WebSocketHandler):
    def open(self):
        self.application.webSocketsPool.append(self)

    def on_message(self, message):
        db = self.application.db
        message_dict = json.loads(message)
        db.chat.insert(message_dict)
        for key, value in enumerate(self.application.webSocketsPool):
            if value != self:
                value.ws_connection.write_message(message)

    def on_close(self, message=None):
        for key, value in enumerate(self.application.webSocketsPool):
            if value == self:
                del self.application.webSocketsPool[key]


# class BaseHandler(tornado.web.RequestHandler):
#     def get_current_user(self):
#         user_json = self.get_secure_cookie("user")
#         if user_json:
#             return user_json
#         else:
#             return None

class BaseHandler(tornado.web.RequestHandler):
    def get_login_url(self):
        return u"/login"

    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        if user_json:
            return tornado.escape.json_decode(user_json)
        else:
            return None

    # Allows us to get the previous URL
    def get_referring_url(self):
        try:
            _, _, referer, _, _, _ = urlparse.urlparse(self.request.headers.get('Referer'))
            if referer:
                return referer
        # Test code will throw this if there was no 'previous' page
        except AttributeError:
            pass
        return '/'

    def get_flash(self):
        flash = self.get_secure_cookie('flash')
        self.clear_cookie('flash')
        return flash

    def get_essentials(self):
        mp = {k: ''.join(v) for k, v in self.request.arguments.iteritems()}
        print mp



# @tornado.web.authenticated
class RegisterHandler(BaseHandler):
    def get(self):
        self.render("registration.html")

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")

        if username and password:
            user = {'id': uuid.uuid4(), 'username': username, 'password': password, 'email': 'adubnyak@gmail.com', 'm': 1}
            users.insert(user)
            self.redirect('/')


class LoginHandler(BaseHandler):
    def get(self):
        self.render("login.html", notification=self.get_flash())

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")

        user = users.find_one({'username': username})

        if user and user['password'] and user['password'] == password:
            self.set_current_user(username)
            self.redirect("/")
        else:
            self.set_secure_cookie('flash', "Login incorrect")
            self.redirect(u"/register")

    def set_current_user(self, user):
        print "setting " + user
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")
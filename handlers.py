import urlparse
import uuid
import json
from bson import ObjectId

import tornado.web
import tornado.ioloop
import tornado.websocket

from pymongo import MongoClient
client = MongoClient('mongodb://chat_user:123@ds031651.mongolab.com:31651/chat')
# client = MongoClient('mongodb://alex:123@ds031551.mongolab.com:31551/chat_clone')
# client = MongoClient('mongodb://alex:123@ds031571.mongolab.com:31571/chat2')
# client = MongoClient('mongodb://alex_user:123@ds031571.mongolab.com:31571/tornado')

# DEGUG = False
#
# if DEGUG:
#     client = MongoClient()
# else:
#     client = MongoClient('mongodb://chat_user:123@ds031651.mongolab.com:31651/chat')

db = client.chat

users = db.users
channels = db.channels
messages = db.messages


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


class MainHandler(BaseHandler):
    def get(self, channel=None, *args, **kwargs):

        if not self.current_user:
            self.redirect("/login")
            return

        # Create first channel
        if not channels.find().count():
            channels.insert(dict(name='Default'))

        context = {
            'channels': channels.find(),
            'current_channel': None
        }

        if channel:
            channel = channels.find_one({'_id': ObjectId(channel)}) or None
            if channel:
                context['current_channel'] = channel['_id']

        if not channel:
            context['current_channel'] = context['channels'][0]['_id']

        context['channel_messages'] = messages.find({'channel': context['current_channel']})
        self.render('index.html', **context)


class WebSocket(tornado.websocket.WebSocketHandler):
    channel_id = None
    cuurent_user = None

    def open(self, *args, **kwargs):
        self.channel_id = args[0]
        self.current_user = self.get_secure_cookie("user")
        self.application.webSocketsPool.append(self)

    def on_message(self, message):
        message_dict = json.loads(message)

        if not self.current_user:
            print('Error! Unauthorized')
            return

        if not channels.find_one({'_id': ObjectId(message_dict['channel'])}):
            print('Error! Wrong channel')
            return

        message_dict.update({
            'user': self.current_user,
            'channel': ObjectId(message_dict['channel'])
        })
        messages.insert(message_dict)

        # Sent message to other users
        for key, value in enumerate(self.application.webSocketsPool):
            if value != self and value.channel_id == self.channel_id:
                value.ws_connection.write_message(message)

    def on_close(self, message=None):
        for key, value in enumerate(self.application.webSocketsPool):
            if value == self:
                del self.application.webSocketsPool[key]


# @tornado.web.authenticated
class RegisterHandler(BaseHandler):
    def get(self):
        self.render("registration.html")

    def post(self):
        username = self.get_argument("username", None)
        password = self.get_argument("password", None)
        email = self.get_argument("email", None)

        if username and password:
            # user = {'id': uuid.uuid4(), 'username': username, 'password': password, 'email': email}
            user = {'id': uuid.uuid4(), 'username': username, 'password': password}
            users.insert(user)
            self.redirect('/')


class LoginHandler(BaseHandler):
    def get(self):
        self.render("login.html")

    def post(self):
        username = self.get_argument("username", None)
        password = self.get_argument("password", None)

        user = users.find_one({'username': username})

        if user and user['password'] and user['password'] == password:
            self.set_current_user(username)
            self.redirect("/")
        else:
            self.set_secure_cookie('flash', "Login incorrect")
            self.redirect(u"/register")

    def set_current_user(self, user):
        print "Welcome " + user
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")


class LogoutHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.clear_cookie("user")
        self.redirect('/')


class CreateChannelHandler(BaseHandler):
    def post(self, *args, **kwargs):
        channel_name = self.get_argument("channel_name", None)
        if channel_name:
            if not channels.find_one({"name": channel_name}):
                channels.insert(dict(name=channel_name))
        self.redirect("/")
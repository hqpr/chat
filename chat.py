#!-*- coding: utf-8 -*-
"""
http://api.mongodb.org/python/current/tutorial.html
http://tornado.readthedocs.org/en/latest/guide/security.html
https://github.com/bootandy/tornado_sample/blob/master/sample/handlers/handlers.py
"""
import base64
import os
import uuid
import pymongo
import tornado.web
import tornado.ioloop
import tornado.websocket

from handlers import CreateChannelHandler, MainHandler, RegisterHandler, LoginHandler, LogoutHandler, WebSocket


class Application(tornado.web.Application):
    def __init__(self):
        self.webSocketsPool = []

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug=True,
            cookie_secret=base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
            login_url='/login'
        )
        connection = pymongo.Connection('127.0.0.1', 27017)
        self.db = connection.chat
        handlers = (
            (r'/', MainHandler),
            (r'/channel/(.*)', MainHandler),
            (r'/create_channel', CreateChannelHandler),
            (r'/register', RegisterHandler),
            (r'/login', LoginHandler),
            (r'/logout', LogoutHandler),
            (r'/websocket/(.*)?', WebSocket),
            (r'/static/(.*)', tornado.web.StaticFileHandler,
             {'path': 'static/'}),
        )

        tornado.web.Application.__init__(self, handlers, **settings)

application = Application()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    application.listen(port)
    tornado.ioloop.IOLoop.instance().start()

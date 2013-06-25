from flask import Flask
from peewee import *
import os,sys
from flask.ext.login import LoginManager
from config import PATH_NAME, DATABASE
os.chdir(PATH_NAME)


s = os.getcwd()
print >> sys.stderr, "directory --------->"
print >> sys.stderr, s

app = Flask(__name__)
print >> sys.stderr, "after app = Flask(__name__)"
app.config.from_object('config')

try:
    database = SqliteDatabase(DATABASE, threadlocals=True)
    s = os.getcwd()
    print >> sys.stderr, "directory within database try --------->"
    print >> sys.stderr, s
    print >> sys.stderr, DATABASE

except:
    print >> sys.stderr, str(sys.exc_info()[0])
    print >> sys.stderr, str(sys.exc_info()[1])
    s = os.getcwd()
    print >> sys.stderr, "directory within except --------->"
    print >> sys.stderr, s

database.connect()

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

from vapp.models import *
from vapp import views




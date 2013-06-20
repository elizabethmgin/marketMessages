from flask import Flask
from peewee import *
import os,sys
os.chdir('/home/ginontherocks/public_python/marketMessages/deploy')


DATABASE = '/home/ginontherocks/public_python/marketMessages/deploy/vapp/USATest.db'
s = os.getcwd()
print >> sys.stderr, "directory --------->"
print >> sys.stderr, s

app = Flask(__name__)
print >> sys.stderr, "after app = Flask(__name__)"
app.config.from_object('config')
print >> sys.stderr, "after app.config.from_object('config')"

try:
    database = SqliteDatabase(DATABASE, threadlocals=True)
except:
    print >> sys.stderr, str(sys.exc_info()[0])
    print >> sys.stderr, str(sys.exc_info()[1])

database.connect()

from vapp import views, models




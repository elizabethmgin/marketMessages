import sys
sys.path.insert(0, '/opt/local/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/')

from vapp import app
app.run('10.0.1.3')
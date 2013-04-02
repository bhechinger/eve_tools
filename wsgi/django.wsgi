import os, sys

#dev
#path = '/home/wonko/projects/eve_tools'
#prod
path = '/usr/local/www/apache22/wsgi/eve_tools'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'eve_tools.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

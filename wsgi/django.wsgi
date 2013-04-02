import os, sys

path = '/home/wonko/projects/eve_tools'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'eve_tools.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

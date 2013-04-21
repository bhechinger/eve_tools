from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView

from EFP import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^(?P<ship_id>\d+)/(?P<systemID>.+)/[Tt][Ee][Xx][Tt]/$', 'EFP.views.text', name='text'),
	url(r'^(?P<ship_id>\d+)/(?P<systemID>.+)/[Hh][Tt][Mm][Ll]/$', 'EFP.views.html', name='html'),
	url(r'^(?P<ship_id>\d+)/(?P<systemID>.+)/[Xx][Mm][Ll]/$', 'EFP.views.xml', name='xml'),
	url(r'^(?P<ship_id>\d+)/(?P<systemID>.+)/[Jj][Ss][Oo][Nn]/$', 'EFP.views.json', name='json'),
	url(r'^(?P<ship_id>\d+)/[Xx][Mm][Ll]_[Ff][Ii][Tt]/$', 'EFP.views.xml_fit', name='xml_fit'),
)

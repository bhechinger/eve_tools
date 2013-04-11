from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView

from EFP import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^(?P<ship_id>\d+)/(?P<systemID>.+)/text/$', 'EFP.views.text', name='text'),
	url(r'^(?P<ship_id>\d+)/(?P<systemID>.+)/html/$', 'EFP.views.html', name='html'),
)

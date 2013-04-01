from django.conf.urls import patterns, url
from django.views.generic import DetailView, ListView

from EFP import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
)

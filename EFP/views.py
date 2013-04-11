from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django import forms
from EFP.models import Invnames, Fitting
import pickle
from GFP import GetFittingPrice

staticDB = 'eve_static'
invNames = Invnames.objects.using(staticDB)
system_list = (
	('Jita', 'Jita'),
	('Rens', 'Rens'),
	('Amarr', 'Amarr'),
	('Dodixie', 'Dodixie')
)

class FitForm(forms.Form):
	system = forms.ChoiceField(choices=system_list)
	fit = forms.CharField(widget=forms.Textarea, required=False)
	file  = forms.FileField(required=False)

def index(request):
	if request.method == 'POST': # If the form has been submitted...
		form = FitForm(request.POST, request.FILES) # A form bound to the POST data
		if form.is_valid(): # All validation rules pass
			#output, badItemList = GFP.get_fit_price(form.cleaned_data, request.FILES)
			doit = GetFittingPrice()
			output, badItemList, error_message = doit.get_fit_price(form.cleaned_data)
			return render(request, 'EFP/results.html', {
				'error_message': error_message,
				'output': output,
				'badItemList': badItemList,
			})
	else:
		form = FitForm() # An unbound form

	return render(request, 'EFP/index.html', {
		'form': form,
	})

def html(request, ship_id, systemID):
	doit = GetFittingPrice()
	output, badItemList, error_message = doit.get_from_db(ship_id, systemID)
	return render(request, 'EFP/results.html', {
		'error_message': error_message,
		'output': output,
		'badItemList': badItemList,
	})

def text(request, ship_id):
	ship_data = get_object_or_404(Fitting, pk=ship_id)
	ship = pickle.loads(ship_data.fitting)
	return render(request, 'EFP/text.html', {
		'ship': ship
	})


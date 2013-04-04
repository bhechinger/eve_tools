from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django import forms
from EFP.models import Invnames
import GFP

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
	fit = forms.CharField(widget=forms.Textarea)
	file  = forms.FileField(required=False)

def index(request):
	if request.method == 'POST': # If the form has been submitted...
		form = FitForm(request.POST, request.FILES) # A form bound to the POST data
		if form.is_valid(): # All validation rules pass
			#output, badItemList = GFP.get_fit_price(form.cleaned_data, request.FILES)
			output, badItemList = GFP.get_fit_price(form.cleaned_data)
			return render(request, 'EFP/results.html', {
				'output': output,
				'badItemList': badItemList,
			})
	else:
		form = FitForm() # An unbound form

	return render(request, 'EFP/index.html', {
		'form': form,
	})

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django import forms

from EFP.models import Fitting

import GFP

class FitForm(forms.Form):
	fit = forms.CharField(widget=forms.Textarea)

def index(request):
	if request.method == 'POST': # If the form has been submitted...
		form = FitForm(request.POST) # A form bound to the POST data
		if form.is_valid(): # All validation rules pass
			output = GFP.get_fit_price(form.cleaned_data['fit'])
			#return HttpResponse(output) # Redirect after POST
			return render(request, 'EFP/results.html', {
				'output': output,
			})
	else:
		form = FitForm() # An unbound form

	return render(request, 'EFP/index.html', {
		'form': form,
	})

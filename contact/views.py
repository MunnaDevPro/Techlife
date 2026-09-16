from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from .forms import ContactOrSupportForm

def contact_or_support_view(request):
    if request.method == 'POST':
        form = ContactOrSupportForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            if request.user.is_authenticated:
                contact.user = request.user
            contact.save()
            messages.success(request, "Thank you! Your message has been submitted successfully.")
        else:
            messages.error(request, "Failed to submit message. Please check the fields and try again.")

        if request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = "/contact/"
            return response
        return redirect('contact_page')

    return redirect('contact_page')

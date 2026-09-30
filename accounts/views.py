from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView


class SignupView(CreateView):
    form_class = UserCreationForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        # Check before both GET and POST; hiding the link alone is not authorization.
        if not settings.PUBLIC_SIGNUP_ENABLED:
            raise Http404
        if request.user.is_authenticated:
            return redirect("tasks:list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your account is ready. Sign in to begin.")
        return response

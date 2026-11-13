from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from apps.clubroom.forms import LoginForm, RegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect("clubroom:home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("clubroom:home")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


class ClubLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class ClubLogoutView(LogoutView):
    pass

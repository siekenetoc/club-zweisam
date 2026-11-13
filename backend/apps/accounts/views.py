from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.accounts.gdpr import delete_user_data, export_user_data
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


@login_required
def data_export(request):
    payload = export_user_data(request.user)
    response = JsonResponse(
        payload,
        encoder=DjangoJSONEncoder,
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )
    response["Content-Disposition"] = 'attachment; filename="club-zweisam-export.json"'
    return response


@login_required
def delete_account(request):
    if request.method == "POST":
        password = request.POST.get("password", "")
        if not request.user.check_password(password):
            messages.error(request, "Passwort ist nicht korrekt.")
            return redirect("accounts:delete")
        if request.POST.get("confirm") != "1":
            messages.error(request, "Löschung muss bestätigt werden.")
            return redirect("accounts:delete")
        user = request.user
        logout(request)
        delete_user_data(user)
        messages.success(
            request,
            "Konto anonymisiert und personenbezogene Inhalte gelöscht. "
            "Audit-Einträge bleiben aus Sicherheitsgründen pseudonym erhalten.",
        )
        return redirect("clubroom:home")
    return render(request, "accounts/delete.html")

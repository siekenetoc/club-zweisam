from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"


class HealthView(View):
    def get(self, request):
        return JsonResponse({"status": "ok", "service": "club-zweisam"})

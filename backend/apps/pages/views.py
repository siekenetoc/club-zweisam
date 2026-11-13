from django.shortcuts import get_object_or_404, render

from apps.pages.models import StaticPage


def page_detail(request, slug):
    page = get_object_or_404(StaticPage, slug=slug, is_published=True)
    return render(request, "pages/page.html", {"page": page})

from apps.pages.models import LandingSection, LandingSettings, NavigationItem


def site_content(request):
    authenticated = request.user.is_authenticated
    nav_items = NavigationItem.objects.filter(is_active=True).order_by("location", "order", "id")
    header_items = [
        item
        for item in nav_items
        if item.location == NavigationItem.LOCATION_HEADER
        and (authenticated or not item.requires_authentication)
    ]
    footer_items = [
        item
        for item in nav_items
        if item.location == NavigationItem.LOCATION_FOOTER
        and (authenticated or not item.requires_authentication)
    ]
    return {
        "landing": LandingSettings.load(),
        "landing_sections": LandingSection.objects.filter(is_active=True),
        "nav_header_items": header_items,
        "nav_footer_items": footer_items,
    }

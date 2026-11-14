from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class StaticPage(TimestampedModel):
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    content_html = models.TextField()
    is_published = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_static_pages",
    )

    class Meta:
        verbose_name = "Statische Seite"
        verbose_name_plural = "Statische Seiten"
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.title

    @property
    def media_items(self):
        return self.media_items_rel.all()


class PageMedia(TimestampedModel):
    page = models.ForeignKey(StaticPage, on_delete=models.CASCADE, related_name="media_items_rel")
    file = models.ImageField(upload_to="pages/")
    alt_text = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Seiten-Medium"
        verbose_name_plural = "Seiten-Medien"
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return self.alt_text or self.file.name


class LandingSettings(models.Model):
    hero_kicker = models.CharField(max_length=120, default="Privater Raum für zwei")
    hero_title = models.CharField(max_length=160, default="Der Raum steht.")
    hero_text = models.TextField(
        default=(
            "Club Zweisam ist ein geschützter Kommunikations- und Spielraum für Paare. "
            "Consent vor Spiel, Nein ist neutral, Geheimnis schützt."
        )
    )
    primary_cta_label = models.CharField(max_length=60, default="Clubraum gründen")
    primary_cta_url = models.CharField(max_length=300, default="/clubraum/neu/")
    secondary_cta_label = models.CharField(max_length=60, default="Anmelden")
    secondary_cta_url = models.CharField(max_length=300, default="/anmelden/")

    class Meta:
        verbose_name = "Landing-Einstellungen"
        verbose_name_plural = "Landing-Einstellungen"

    def __str__(self) -> str:
        return "Landing-Einstellungen"

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]


class LandingSection(TimestampedModel):
    title = models.CharField(max_length=160)
    body_html = models.TextField(blank=True)
    link_label = models.CharField(max_length=80, blank=True)
    link_url = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Landing-Bereich"
        verbose_name_plural = "Landing-Bereiche"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title


class NavigationItem(TimestampedModel):
    LOCATION_HEADER = "header"
    LOCATION_FOOTER = "footer"
    LOCATION_CHOICES = (
        (LOCATION_HEADER, "Kopfmenü"),
        (LOCATION_FOOTER, "Fußzeile"),
    )

    label = models.CharField(max_length=80)
    url = models.CharField(max_length=300)
    location = models.CharField(max_length=16, choices=LOCATION_CHOICES, default=LOCATION_FOOTER)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    requires_authentication = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Menüeintrag"
        verbose_name_plural = "Menüeinträge"
        ordering = ["location", "order", "id"]

    def __str__(self) -> str:
        return f"{self.label} ({self.get_location_display()})"

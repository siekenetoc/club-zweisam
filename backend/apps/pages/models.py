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

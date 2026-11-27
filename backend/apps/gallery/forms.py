from django import forms

from apps.clubroom.forms import StyledFormMixin
from apps.gallery.models import Album, GalleryImage


class AlbumForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Album
        fields = ("title", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        labels = {"title": "Albumtitel", "description": "Beschreibung (optional)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class ImageUploadForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = GalleryImage
        fields = ("image", "caption")
        labels = {"image": "Bild", "caption": "Erinnerung (optional)"}
        widgets = {"caption": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

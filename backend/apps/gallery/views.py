from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.clubroom.models import Membership
from apps.clubroom.permissions import OWNER
from apps.gallery.forms import AlbumForm, ImageUploadForm
from apps.gallery.models import Album, GalleryImage
from apps.gallery.services import delete_gallery_image, process_gallery_image


def _owner(request):
    membership = (
        Membership.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
            clubroom__deleted_at__isnull=True,
        )
        .select_related("clubroom")
        .first()
    )
    if (
        membership is None
        or membership.role != OWNER
        or not membership.has_module_access("gallery")
    ):
        raise PermissionDenied("Kein Zugriff auf die Galerie.")
    return membership


@login_required
def index(request):
    membership = _owner(request)
    clubroom = membership.clubroom
    albums = Album.objects.filter(clubroom=clubroom).prefetch_related("images")
    album_form = AlbumForm()
    upload_form = ImageUploadForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "album":
            album_form = AlbumForm(request.POST)
            if album_form.is_valid():
                album = album_form.save(commit=False)
                album.clubroom = clubroom
                album.created_by = request.user
                album.save()
                messages.success(request, "Album angelegt.")
                return redirect("gallery:index")
        elif action == "image":
            album = get_object_or_404(Album, pk=request.POST.get("album"), clubroom=clubroom)
            upload_form = ImageUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                image = upload_form.save(commit=False)
                image.album = album
                image.uploaded_by = request.user
                if image.image.size > 15 * 1024 * 1024:
                    messages.error(request, "Bild ist größer als 15 MB.")
                else:
                    try:
                        main, thumb, width, height = process_gallery_image(
                            upload_form.cleaned_data["image"]
                        )
                    except Exception:
                        messages.error(request, "Bild konnte nicht verarbeitet werden.")
                    else:
                        image.image.name = main
                        image.thumb.name = thumb
                        image.width = width
                        image.height = height
                        image.save()
                        messages.success(request, "Bild hinzugefügt.")
                        return redirect("gallery:index")
    return render(
        request,
        "gallery/index.html",
        {
            "clubroom": clubroom,
            "albums": albums,
            "album_form": album_form,
            "upload_form": upload_form,
            "allows_upload": True,
        },
    )


@login_required
def image_file(request, pk):
    membership = _owner(request)
    image = get_object_or_404(GalleryImage, pk=pk, album__clubroom=membership.clubroom)
    if not image.image:
        raise Http404
    return FileResponse(
        image.image.open("rb"),
        content_type="image/webp",
        as_attachment=False,
        filename=image.image.name.rsplit("/", 1)[-1],
    )


@login_required
def thumb_file(request, pk):
    membership = _owner(request)
    image = get_object_or_404(GalleryImage, pk=pk, album__clubroom=membership.clubroom)
    if not image.thumb:
        raise Http404
    return FileResponse(image.thumb.open("rb"), content_type="image/webp")


@login_required
@require_POST
def delete_image(request, pk):
    membership = _owner(request)
    image = get_object_or_404(GalleryImage, pk=pk, album__clubroom=membership.clubroom)
    delete_gallery_image(image)
    image.delete()
    messages.success(request, "Bild gelöscht.")
    return redirect("gallery:index")

from apps.vitrine.models import SOURCE_MATCH, Commonality


def record_commonality(*, clubroom, source_type, source_id, category):
    return Commonality.objects.get_or_create(
        clubroom=clubroom,
        source_type=source_type,
        source_id=source_id,
        defaults={"category": category},
    )


def record_match_commonality(*, match):
    return record_commonality(
        clubroom=match.round.clubroom,
        source_type=SOURCE_MATCH,
        source_id=match.pk,
        category=match.question.deck.title,
    )

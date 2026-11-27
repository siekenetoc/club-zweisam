MODULES = (
    "lounge",
    "roulette",
    "vitrine",
    "wishes",
    "playbook",
    "feed",
    "deep_talk",
    "points",
)

MODULE_LABELS = {
    "lounge": "Lounge",
    "roulette": "Séparée",
    "vitrine": "Vitrine",
    "wishes": "Concierge",
    "playbook": "Playbook",
    "feed": "Logbuch",
    "deep_talk": "Deep Talk",
    "points": "Punkte",
}

OWNER = "owner"
MODERATOR = "moderator"
ADVISOR = "advisor"
MEDIATOR = "mediator"
GUEST = "guest"

ROLE_CHOICES = (
    (OWNER, "Hauptmitglied"),
    (MODERATOR, "Moderator"),
    (ADVISOR, "Berater"),
    (MEDIATOR, "Mediator"),
    (GUEST, "Gast/Beobachter"),
)

ROLE_LABELS = dict(ROLE_CHOICES)

INVITABLE_ROLES = (OWNER, MODERATOR, ADVISOR, MEDIATOR, GUEST)
INVITABLE_ROLE_CHOICES = tuple(
    (value, label) for value, label in ROLE_CHOICES if value in INVITABLE_ROLES
)

ROLE_PERMISSIONS = {
    OWNER: {module: True for module in MODULES},
    MODERATOR: {"lounge": True, "feed": True},
    ADVISOR: {"lounge": True, "deep_talk": True},
    MEDIATOR: {"lounge": True, "deep_talk": True},
    GUEST: {"lounge": True},
}

READ_ONLY_ROLES = frozenset({GUEST})


def default_permissions_for(role: str) -> dict[str, bool]:
    template = ROLE_PERMISSIONS.get(role, {})
    return {module: bool(template.get(module, False)) for module in MODULES}


def role_can_write(role: str) -> bool:
    return role not in READ_ONLY_ROLES

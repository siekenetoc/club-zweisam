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
SEX_PARTNER = "sex_partner"
GUEST = "guest"

ROLE_CHOICES = (
    (OWNER, "Hauptmitglied"),
    (MODERATOR, "Moderator"),
    (ADVISOR, "Berater"),
    (MEDIATOR, "Mediator"),
    (SEX_PARTNER, "Sex-Partner"),
    (GUEST, "Gast/Beobachter"),
)

ROLE_LABELS = dict(ROLE_CHOICES)

ROLE_PERMISSIONS = {
    OWNER: {module: True for module in MODULES},
    MODERATOR: {"lounge": True, "feed": True},
    ADVISOR: {"lounge": True, "deep_talk": True},
    MEDIATOR: {"lounge": True, "deep_talk": True},
    SEX_PARTNER: {"lounge": True, "playbook": True},
    GUEST: {"lounge": True},
}

READ_ONLY_ROLES = frozenset({GUEST})


def default_permissions_for(role: str) -> dict[str, bool]:
    template = ROLE_PERMISSIONS.get(role, {})
    return {module: bool(template.get(module, False)) for module in MODULES}


def role_can_write(role: str) -> bool:
    return role not in READ_ONLY_ROLES

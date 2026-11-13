SENSITIVE_MODEL_LABELS = frozenset(
    {
        "roulette.secretanswer",
        "roulette.boundary",
        "wishes.wish",
        "wishes.fantasywish",
    }
)


def is_sensitive_model(model) -> bool:
    return model._meta.label_lower in SENSITIVE_MODEL_LABELS


def is_sensitive_label(label: str) -> bool:
    return label.lower() in SENSITIVE_MODEL_LABELS

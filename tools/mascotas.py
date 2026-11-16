# SPDX-License-Identifier: AGPL-3.0-or-later
"""Adopción de cachorros y gatitos. El catálogo vive en data/vida.json."""
import mundos


def breeds(species=None):
    pets = mundos.catalog().get('pets') or {}
    if species:
        return list(pets.get(species) or [])
    found = []
    for key in ('dog', 'cat'):
        found.extend(pets.get(key) or [])
    return found


def validate(raw):
    """Devuelve la mascota guardable, o None si la raza o el color no existen."""
    if not isinstance(raw, dict):
        return None
    species = raw.get('species')
    if species not in ('dog', 'cat'):
        return None
    breed = next((item for item in breeds(species) if item.get('id') == raw.get('breed')), None)
    if not breed:
        return None
    colors = breed.get('colors') or []
    if not 3 <= len(colors) <= 4:
        return None
    try:
        variant = int(raw.get('variant', 0))
    except (TypeError, ValueError):
        return None
    if variant < 0 or variant >= len(colors):
        return None
    import accounts as acc
    name = acc.game_name(raw.get('name') or breed.get('name') or '')
    if not name:
        name = str(breed.get('name') or 'Mascota')[:16]
    return {
        'species': species,
        'breed': breed['id'],
        'variant': variant,
        'name': name[:16],
    }

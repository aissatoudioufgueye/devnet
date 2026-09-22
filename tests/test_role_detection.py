"""
Test unitaire de la détection de rôle (fonction pure) demandé au
cahier des charges §3.2.5.

Lancer avec : pytest tests/
"""

import sys
from pathlib import Path

# Permet d'importer automation.py à la racine du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation import detect_role


def test_detect_role_routeur():
    assert detect_role("R1-DKR") == "routeur"
    assert detect_role("R2-ABJ") == "routeur"
    assert detect_role("R3-SL") == "routeur"  # extension bonus, 3e site


def test_detect_role_core():
    assert detect_role("SW1-CORE") == "core"
    assert detect_role("SW2-CORE") == "core"
    assert detect_role("SW5-CORE") == "core"  # extension bonus, 3e site


def test_detect_role_acces():
    assert detect_role("SW3-ACC") == "acces"
    assert detect_role("SW4-ACC") == "acces"
    assert detect_role("SW6-ACC") == "acces"  # extension bonus, 3e site


def test_detect_role_inconnu():
    assert detect_role("PC1") == "inconnu"
    assert detect_role("") == "inconnu"

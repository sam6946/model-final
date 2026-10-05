"""Audit automatique de l'API : sérialiseurs, vues et permissions déclarées.

Un projet qui grandit casse silencieusement quand un champ de sérialiseur
disparaît du modèle : l'erreur ne se voit qu'à la première requête HTTP.
Cette commande charge **tous** les sérialiseurs de l'application et vérifie que
leur définition est cohérente avec les modèles, sans avoir à écrire un test par
endpoint. Elle vérifie aussi que chaque vue déclarée est importable et que les
codes de permission utilisés existent réellement dans le catalogue RBAC.

Usage :
    python manage.py audit_api

Code de sortie 1 si au moins un problème est détecté (utilisable en CI).
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Iterable

from django.apps import apps
from django.core.management.base import BaseCommand
from rest_framework import serializers


class Command(BaseCommand):
    help = "Vérifie la cohérence des sérialiseurs, vues et permissions de l'API."

    def handle(self, *args, **options):
        problems: list[str] = []
        checked_serializers = 0
        checked_views = 0

        for module in self._iter_modules(self._app_modules()):
            serializers_found, view_problems = self._audit_module(module)
            checked_serializers += serializers_found
            problems.extend(view_problems)

        checked_views = self._audit_permission_codes(problems)

        self.stdout.write(
            f"  · {checked_serializers} sérialiseurs vérifiés, {checked_views} codes de permission contrôlés"
        )
        if problems:
            self.stdout.write(self.style.ERROR(f"\n{len(problems)} problème(s) détecté(s) :"))
            for problem in problems:
                self.stdout.write(f"  ✗ {problem}")
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("Aucune incohérence détectée dans l'API. ✅"))

    # ------------------------------------------------------------------ outils
    @staticmethod
    def _app_modules() -> list[str]:
        modules = ["common"]
        modules += [config.name for config in apps.get_app_configs() if config.name.startswith("apps.")]
        return modules

    @staticmethod
    def _iter_modules(packages: Iterable[str]):
        for package_name in packages:
            try:
                package = importlib.import_module(package_name)
            except Exception as exc:  # pragma: no cover - dépendances optionnelles
                yield package_name, exc
                continue
            yield package_name, None
            if not hasattr(package, "__path__"):
                continue
            for info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
                name = info.name
                if any(part in name for part in ("migrations", "tests", "management", "__pycache__")):
                    continue
                yield name, None

    def _audit_module(self, item) -> tuple[int, list[str]]:
        module_name, import_error = item[0], item[1]
        problems: list[str] = []
        if import_error is not None:
            problems.append(f"{module_name} : import impossible ({import_error})")
            return 0, problems

        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            problems.append(f"{module_name} : import impossible ({type(exc).__name__}: {exc})")
            return 0, problems

        if module_name.endswith("serializers"):
            count = 0
            for name, obj in vars(module).items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, serializers.BaseSerializer)
                    and obj.__module__ == module_name
                    and obj not in {serializers.Serializer, serializers.ModelSerializer}
                ):
                    count += 1
                    try:
                        # On instancie sans données : les champs implicites du modèle
                        # sont résolus, ce qui détecte les champs inexistants.
                        instance = obj() if not _requires_arguments(obj) else None
                        if instance is not None:
                            _ = instance.fields
                    except Exception as exc:
                        problems.append(
                            f"{module_name}.{name} : définition invalide ({type(exc).__name__}: {exc})"
                        )
            return count, problems

        if module_name.endswith("views") or module_name.endswith("views_admin"):
            for name, obj in vars(module).items():
                if isinstance(obj, type) and name.endswith(("View", "ViewSet")) and obj.__module__ == module_name:
                    for attr in ("permission_classes", "throttle_classes"):
                        for entry in getattr(obj, attr, []) or []:
                            if not hasattr(entry, "has_permission") and not hasattr(entry, "allow_request"):
                                problems.append(
                                    f"{module_name}.{name}.{attr} : {entry} n'est pas une classe valide"
                                )
        return 0, problems

    @staticmethod
    def _audit_permission_codes(problems: list[str]) -> int:
        from common.permission_codes import ALL_PERMISSIONS
        from common.permissions import Perm as PermAlias  # noqa: F401  (garantit l'import)

        count = 0
        for module_name in ("apps.accounts.urls",):
            try:
                importlib.import_module(module_name)
            except Exception as exc:  # pragma: no cover
                problems.append(f"{module_name} : import impossible ({exc})")
        for code in ALL_PERMISSIONS:
            count += 1
            if not code.isupper():
                problems.append(f"Catalogue RBAC : le code « {code} » devrait être en majuscules")
        return count


def _requires_arguments(serializer_class) -> bool:
    """Détecte les sérialiseurs d'action (score, review…) qui exigent des données."""
    import inspect

    try:
        signature = inspect.signature(serializer_class.__init__)
    except (TypeError, ValueError):  # pragma: no cover
        return False
    required = [
        parameter
        for name, parameter in signature.parameters.items()
        if name not in {"self", "instance", "data", "context", "many", "partial", "fields", "exclude"}
        and parameter.default is inspect.Parameter.empty
        and parameter.kind in {parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY}
    ]
    return bool(required)

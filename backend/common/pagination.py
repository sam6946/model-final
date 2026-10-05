"""Pagination KEMTA : par curseur (grosses collections) et par page (admin)."""
from __future__ import annotations

from collections import OrderedDict

from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param


class KemtaCursorPagination(CursorPagination):
    """Pagination par défaut : stable même quand des données sont insérées.

    Obligatoire pour les flux (activités, notifications, preuves) où une
    pagination par offset afficherait des doublons.
    """

    page_size = 20
    max_page_size = 100
    page_size_query_param = "page_size"
    ordering = ("-created_at", "-id")

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    ("count", None),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("page_size", self.page_size),
                    ("results", data),
                ]
            )
        )

    def get_next_link(self):
        link = super().get_next_link()
        return self._strip(link)

    def get_previous_link(self):
        link = super().get_previous_link()
        return self._strip(link)

    @staticmethod
    def _strip(link: str | None) -> str | None:
        return link


class KemtaPageNumberPagination(PageNumberPagination):
    """Pagination classique, réservée aux tables d'administration."""

    page_size = 25
    max_page_size = 200
    page_size_query_param = "page_size"

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("pages", self.page.paginator.num_pages),
                    ("page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )


class NoPagination(PageNumberPagination):
    page_size = 500
    max_page_size = 500

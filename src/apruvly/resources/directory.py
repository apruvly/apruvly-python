"""Directory (areas and people) endpoints."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from apruvly._http import path_escape
from apruvly.models.common import to_dict
from apruvly.models.directory import (
    DirectoryArea,
    DirectoryAreaInput,
    DirectoryBulkAreasResponse,
    DirectoryBulkPeopleResponse,
    DirectoryPeopleList,
    DirectoryPerson,
    DirectoryPersonInput,
)

if TYPE_CHECKING:
    from apruvly._http import Requestor


class AreasResource:
    """Directory areas CRUD and bulk operations."""

    def __init__(self, requestor: Requestor) -> None:
        self._http = requestor

    def list(self) -> Sequence[DirectoryArea]:
        """List all areas. Requires ``api:directory:list``."""
        data = self._http.request(
            "GET",
            "/api/v1/directory/areas",
            expected_statuses=(200,),
        )
        rows = data or []
        return [
            DirectoryArea.from_dict(row) for row in rows if isinstance(row, Mapping)
        ]

    def create(self, area: DirectoryAreaInput | Mapping[str, str]) -> DirectoryArea:
        """Create an area. Requires ``api:directory:write``."""
        body = area.to_dict() if isinstance(area, DirectoryAreaInput) else dict(area)
        data = self._http.request(
            "POST",
            "/api/v1/directory/areas",
            body=body,
            expected_statuses=(201,),
        )
        return DirectoryArea.from_dict(data or {})

    def get(self, area_id: str) -> DirectoryArea:
        """Get an area by id. Requires ``api:directory:read``."""
        data = self._http.request(
            "GET",
            f"/api/v1/directory/areas/{path_escape(area_id)}",
            expected_statuses=(200,),
        )
        return DirectoryArea.from_dict(data or {})

    def update(
        self, area_id: str, area: DirectoryAreaInput | Mapping[str, str]
    ) -> DirectoryArea:
        """Update an area. Requires ``api:directory:write``."""
        body = area.to_dict() if isinstance(area, DirectoryAreaInput) else dict(area)
        data = self._http.request(
            "PUT",
            f"/api/v1/directory/areas/{path_escape(area_id)}",
            body=body,
            expected_statuses=(200,),
        )
        return DirectoryArea.from_dict(data or {})

    def delete(self, area_id: str) -> None:
        """Delete an area. Requires ``api:directory:delete``."""
        self._http.request(
            "DELETE",
            f"/api/v1/directory/areas/{path_escape(area_id)}",
            expected_statuses=(204,),
        )

    def bulk_create(
        self, items: Sequence[DirectoryAreaInput | Mapping[str, str]]
    ) -> DirectoryBulkAreasResponse:
        """Bulk-create areas (max 100). Requires ``api:directory:bulk``."""
        payload = {
            "items": [
                i.to_dict() if isinstance(i, DirectoryAreaInput) else dict(i)
                for i in items
            ]
        }
        data = self._http.request(
            "POST",
            "/api/v1/directory/areas/bulk",
            body=payload,
            expected_statuses=(201,),
        )
        return DirectoryBulkAreasResponse.from_dict(data or {})

    def bulk_update(
        self, items: Sequence[DirectoryAreaInput | Mapping[str, str]]
    ) -> DirectoryBulkAreasResponse:
        """Bulk-update areas (each item needs ``id``). Requires ``api:directory:bulk``."""
        payload = {
            "items": [
                i.to_dict() if isinstance(i, DirectoryAreaInput) else dict(i)
                for i in items
            ]
        }
        data = self._http.request(
            "PUT",
            "/api/v1/directory/areas/bulk",
            body=payload,
            expected_statuses=(200,),
        )
        return DirectoryBulkAreasResponse.from_dict(data or {})


class PeopleResource:
    """Directory people CRUD and bulk operations."""

    def __init__(self, requestor: Requestor) -> None:
        self._http = requestor

    def list(
        self,
        *,
        page: int | None = None,
        q: str | None = None,
        area: str | None = None,
    ) -> DirectoryPeopleList:
        """List people (page size fixed at 25). Requires ``api:directory:list``."""
        data = self._http.request(
            "GET",
            "/api/v1/directory/people",
            params={"page": page, "q": q, "area": area},
            expected_statuses=(200,),
        )
        return DirectoryPeopleList.from_dict(data or {})

    def create(
        self, person: DirectoryPersonInput | Mapping[str, object]
    ) -> DirectoryPerson:
        """Create a person. Requires ``api:directory:write``."""
        body = (
            person.to_dict()
            if isinstance(person, DirectoryPersonInput)
            else to_dict(person)
        )
        data = self._http.request(
            "POST",
            "/api/v1/directory/people",
            body=body,
            expected_statuses=(201,),
        )
        return DirectoryPerson.from_dict(data or {})

    def get(self, person_id: str) -> DirectoryPerson:
        """Get a person by id. Requires ``api:directory:read``."""
        data = self._http.request(
            "GET",
            f"/api/v1/directory/people/{path_escape(person_id)}",
            expected_statuses=(200,),
        )
        return DirectoryPerson.from_dict(data or {})

    def update(
        self, person_id: str, person: DirectoryPersonInput | Mapping[str, object]
    ) -> DirectoryPerson:
        """Update a person. Requires ``api:directory:write``."""
        body = (
            person.to_dict()
            if isinstance(person, DirectoryPersonInput)
            else to_dict(person)
        )
        data = self._http.request(
            "PUT",
            f"/api/v1/directory/people/{path_escape(person_id)}",
            body=body,
            expected_statuses=(200,),
        )
        return DirectoryPerson.from_dict(data or {})

    def delete(self, person_id: str) -> None:
        """Delete a person. Requires ``api:directory:delete``."""
        self._http.request(
            "DELETE",
            f"/api/v1/directory/people/{path_escape(person_id)}",
            expected_statuses=(204,),
        )

    def bulk_create(
        self, items: Sequence[DirectoryPersonInput | Mapping[str, object]]
    ) -> DirectoryBulkPeopleResponse:
        """Bulk-create people (max 1000). Requires ``api:directory:bulk``."""
        payload = {
            "items": [
                i.to_dict() if isinstance(i, DirectoryPersonInput) else to_dict(i)
                for i in items
            ]
        }
        data = self._http.request(
            "POST",
            "/api/v1/directory/people/bulk",
            body=payload,
            expected_statuses=(201,),
        )
        return DirectoryBulkPeopleResponse.from_dict(data or {})

    def bulk_update(
        self, items: Sequence[DirectoryPersonInput | Mapping[str, object]]
    ) -> DirectoryBulkPeopleResponse:
        """Bulk-update people (each item needs ``id``). Requires ``api:directory:bulk``."""
        payload = {
            "items": [
                i.to_dict() if isinstance(i, DirectoryPersonInput) else to_dict(i)
                for i in items
            ]
        }
        data = self._http.request(
            "PUT",
            "/api/v1/directory/people/bulk",
            body=payload,
            expected_statuses=(200,),
        )
        return DirectoryBulkPeopleResponse.from_dict(data or {})


class DirectoryResource:
    """Directory namespace exposing ``areas`` and ``people``."""

    def __init__(self, requestor: Requestor) -> None:
        self.areas = AreasResource(requestor)
        self.people = PeopleResource(requestor)

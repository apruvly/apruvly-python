"""Directory (areas / people) models — snake_case."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from apruvly.models.common import from_mapping, to_dict


@dataclass
class DirectoryContact:
    provider: str
    address: str
    id: str | None = None
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DirectoryContact:
        return from_mapping(cls, data)  # type: ignore[return-value]


@dataclass
class DirectoryArea:
    id: str | None = None
    name: str | None = None
    is_active: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DirectoryArea:
        return from_mapping(cls, data)  # type: ignore[return-value]


@dataclass
class DirectoryAreaInput:
    name: str
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class DirectoryPerson:
    id: str | None = None
    display_name: str | None = None
    is_active: bool | None = None
    area_ids: list[str] = field(default_factory=list)
    contacts: list[DirectoryContact] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DirectoryPerson:
        contacts_raw = data.get("contacts") or []
        return cls(
            id=data.get("id"),
            display_name=data.get("display_name"),
            is_active=data.get("is_active"),
            area_ids=list(data.get("area_ids") or []),
            contacts=[
                DirectoryContact.from_dict(c)
                for c in contacts_raw
                if isinstance(c, Mapping)
            ],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class DirectoryPersonInput:
    display_name: str
    id: str | None = None
    area_ids: list[str] | None = None
    contacts: list[DirectoryContact] | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class DirectoryPeopleList:
    items: list[DirectoryPerson] = field(default_factory=list)
    total: int | None = None
    page: int | None = None
    page_size: int | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DirectoryPeopleList:
        items_raw = data.get("items") or []
        return cls(
            items=[
                DirectoryPerson.from_dict(i)
                for i in items_raw
                if isinstance(i, Mapping)
            ],
            total=data.get("total"),
            page=data.get("page"),
            page_size=data.get("page_size"),
        )


@dataclass
class DirectoryBulkAreasResponse:
    items: list[DirectoryArea] = field(default_factory=list)
    count: int | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DirectoryBulkAreasResponse:
        items_raw = data.get("items") or []
        return cls(
            items=[
                DirectoryArea.from_dict(i) for i in items_raw if isinstance(i, Mapping)
            ],
            count=data.get("count"),
        )


@dataclass
class DirectoryBulkPeopleResponse:
    items: list[DirectoryPerson] = field(default_factory=list)
    count: int | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DirectoryBulkPeopleResponse:
        items_raw = data.get("items") or []
        return cls(
            items=[
                DirectoryPerson.from_dict(i)
                for i in items_raw
                if isinstance(i, Mapping)
            ],
            count=data.get("count"),
        )

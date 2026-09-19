"""Sensors of We Eat, all read from the coordinator snapshot."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WeEatConfigEntry
from .const import DOMAIN
from .coordinator import WeEatCoordinator

DEVICE = DeviceInfo(identifiers={(DOMAIN, "we_eat")}, name="We Eat", manufacturer="We Eat")


async def async_setup_entry(hass, entry: WeEatConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entities: list[WeEatSensor] = [
        MenuSensor(coordinator),
        PlanSensor(coordinator),
        ConsumedSensor(coordinator),
    ]
    if coordinator.kcal_target is not None:
        entities.append(RemainingSensor(coordinator))
    async_add_entities(entities)


class WeEatSensor(CoordinatorEntity[WeEatCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_device_info = DEVICE

    def __init__(self, coordinator: WeEatCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"we_eat_{key}"
        self._attr_name = name


class MenuSensor(WeEatSensor):
    def __init__(self, coordinator: WeEatCoordinator) -> None:
        super().__init__(coordinator, "menu", "Menu")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data["menu_state"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {**self.coordinator.data["menu_attrs"], "favorites": self.coordinator.favorites}


class PlanSensor(WeEatSensor):
    _unrecorded_attributes = frozenset({"days", "draft_days"})

    def __init__(self, coordinator: WeEatCoordinator) -> None:
        super().__init__(coordinator, "piano_settimana", "Piano settimana")

    @property
    def native_value(self) -> str:
        return self.coordinator.data["plan_status"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {"days": data["plan_days"], "draft_days": data["draft_days"]}


class ConsumedSensor(WeEatSensor):
    _attr_native_unit_of_measurement = "kcal"
    _unrecorded_attributes = frozenset({"entries"})

    def __init__(self, coordinator: WeEatCoordinator) -> None:
        super().__init__(coordinator, "kcal_consumate", "Kcal consumate")

    @property
    def native_value(self) -> int:
        return self.coordinator.data["kcal_consumed"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            "by_meal": data["kcal_by_meal"],
            "entries": data["entries_today"],
            "target": data["kcal_target"],
        }


class RemainingSensor(WeEatSensor):
    _attr_native_unit_of_measurement = "kcal"

    def __init__(self, coordinator: WeEatCoordinator) -> None:
        super().__init__(coordinator, "kcal_rimanenti", "Kcal rimanenti")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data["kcal_remaining"]

"""Number entities for A.O. Smith integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode, NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DEVICE_CATEGORY_WATER_HEATER
from .entity import AOSmithEntity

_LOGGER = logging.getLogger(__name__)

# curiesTime 取值范围
CURIES_TIME_MIN = 1
CURIES_TIME_MAX = 99
CURIES_TIME_DEFAULT = 5


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up A.O. Smith number entities from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device_data in coordinator.data.items():
        if str(device_data.get("deviceCategory")) == DEVICE_CATEGORY_WATER_HEATER:
            # 添加一键零冷水运行时长设置
            entities.append(
                AOSmithCuriesTimeNumber(coordinator, device_id)
            )

    _LOGGER.info("Setting up %d number entities", len(entities))
    async_add_entities(entities, True)


class AOSmithCuriesTimeNumber(AOSmithEntity, NumberEntity):
    """Number entity for setting curiesTime (one-key zero cold water runtime)."""

    def __init__(self, coordinator, device_id: str):
        """Initialize the number entity."""
        super().__init__(coordinator, device_id)

        # 从翻译配置获取名称
        translation = getattr(coordinator, 'translation', {})
        entity_config = translation.get('entity', {})
        number_config = entity_config.get('number', {}).get('curies_time', {})

        device_name = self.device_data.get('productName', 'Water Heater')
        number_name = number_config.get('name', '一键零冷水运行时长')

        self._attr_name = f"{device_name} {number_name}"
        self._attr_unique_id = f"{device_id}_curies_time"
        self._attr_icon = number_config.get('icon', 'mdi:timer-cog')
        self._attr_native_unit_of_measurement = number_config.get('unit', '分钟')
        self._attr_device_class = NumberDeviceClass.DURATION

        # 设置数值范围
        self._attr_native_min_value = CURIES_TIME_MIN
        self._attr_native_max_value = CURIES_TIME_MAX
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER

        self._attr_native_value = CURIES_TIME_DEFAULT

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        # 从设备数据中获取当前设置的 curiesTime
        output_data = self._get_output_data()
        if output_data:
            curies_time = output_data.get("curiesTime")
            if curies_time is not None:
                try:
                    return float(curies_time)
                except (ValueError, TypeError):
                    pass
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the curiesTime value."""
        # 限制在有效范围内
        value = max(CURIES_TIME_MIN, min(CURIES_TIME_MAX, int(value)))

        _LOGGER.info(
            "Setting curiesTime to %d minutes for device %s",
            value, self._device_id
        )

        try:
            await self.coordinator.api.async_send_command(
                self._device_id,
                "setCuriesTime",
                {"curiesTime": str(value)}
            )
            self._attr_native_value = value
            self.async_write_ha_state()
            _LOGGER.info(
                "Successfully set curiesTime to %d minutes for device %s",
                value, self._device_id
            )
        except Exception as e:
            _LOGGER.error(
                "Failed to set curiesTime for device %s: %s",
                self._device_id, e
            )

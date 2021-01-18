from datetime import timedelta
import logging

import adafruit_si7021
import board
import busio
import voluptuous as vol

from homeassistant.components.sensor import (
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_HUMIDITY,
    PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_NAME, TEMP_CELSIUS
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Si7021"
SCAN_INTERVAL = timedelta(seconds=15)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3)

CONF_I2C_ADDRESS = "i2c_address"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_I2C_ADDRESS, default=None): cv.positive_int
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    try:
        # initializing I2C bus using the auto-detected pins
        i2c = busio.I2C(board.SCL, board.SDA)
        # initializing the sensor
        si7021 = adafruit_si7021.SI7021(i2c, address=config[CONF_I2C_ADDRESS])
    except ValueError as error:
        # this usually happens when the board is I2C capable, but the device can't be found at the configured address
        if str(error.args[0]).startswith("No I2C device at address"):
            _LOGGER.error(
                "%s. Hint: Check wiring!",
                error.args[0],
            )
            raise PlatformNotReady() from error
        _LOGGER.error(error)
        return
    
    name = config[CONF_NAME]
    add_entities(
        [Si7021TemperatureSensor(si7021, name), Si7021HumiditySensor(Si7021, name)]
    )


class Si7021Sensor(Entity):

    def __init__(
        self,
        si7021: adafruit_si7021.SI7021,
        name: str,
        unit_of_measurement: str,
        device_class: str,
    ):
        """Initialize the sensor."""
        self._si7021 = si7021
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._device_class = device_class
        self._state = None
        self._errored = False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def available(self) -> bool:
        """Return if the device is currently available."""
        return not self._errored


class Si7021TemperatureSensor(Si7021Sensor):

    def __init__(self, bmp280: adafruit_si7021.SI7021, name: str):
        """Initialize the entity."""
        super().__init__(
            si7021, f"{name} Temperature", TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE
        )

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Fetch new state data for the sensor."""
        try:
            self._state = round(self._si7021.temperature, 1)
            if self._errored:
                _LOGGER.warning("Communication restored with temperature sensor")
                self._errored = False
        except OSError:
            # this is thrown when a working sensor is unplugged between two updates
            _LOGGER.warning(
                "Unable to read temperature data due to a communication problem"
            )
            self._errored = True


class Si7021HumiditySensor(Si7021Sensor):

    def __init__(self, bmp280: Adafruit_BMP280_I2C, name: str):
        """Initialize the entity."""
        super().__init__(
            si7021, f"{name} Humidity", "%", DEVICE_CLASS_HUMIDITY
        )

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Fetch new state data for the sensor."""
        try:
            self._state = round(self._si7021.relative_humidity, 1)
            if self._errored:
                _LOGGER.warning("Communication restored with pressure sensor")
                self._errored = False
        except OSError:
            # this is thrown when a working sensor is unplugged between two updates
            _LOGGER.warning(
                "Unable to read pressure data due to a communication problem"
            )
            self._errored = True
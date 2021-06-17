# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:
#
# Copyright 2020, Battelle Memorial Institute.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This material was prepared as an account of work sponsored by an agency of
# the United States Government. Neither the United States Government nor the
# United States Department of Energy, nor Battelle, nor any of their
# employees, nor any jurisdiction or organization that has cooperated in the
# development of these materials, makes any warranty, express or
# implied, or assumes any legal liability or responsibility for the accuracy,
# completeness, or usefulness or any information, apparatus, product,
# software, or process disclosed, or represents that its use would not infringe
# privately owned rights. Reference herein to any specific commercial product,
# process, or service by trade name, trademark, manufacturer, or otherwise
# does not necessarily constitute or imply its endorsement, recommendation, or
# favoring by the United States Government or any agency thereof, or
# Battelle Memorial Institute. The views and opinions of authors expressed
# herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY operated by
# BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830
# }}}
from gevent import monkey
from volttron.platform.agent import utils
from platform_driver.interfaces import BaseRegister, BaseInterface, BasicRevert
from platform_driver.interfaces.modbus_tk import helpers
from platform_driver.interfaces.modbus_tk.maps import Map

import logging
import struct

monkey.patch_socket()

modbus_logger = logging.getLogger("pymodbus")
modbus_logger.setLevel(logging.WARNING)

utils.setup_logging()
_log = logging.getLogger(__name__)


class ModbusTKRegister(BaseRegister):
    """
        Modbus TK register class.

    :param point_name: the register point name
    :param default_value: the default value of writable register
    :param field: modbus client field

    :type point_name: str
    :type default_value: parse str to the register type
    :type field: Field
    """

    def __init__(self, point_name, default_value, field, description=""):
        datatype = "bit" if field.type == helpers.BOOL else "byte"

        super(ModbusTKRegister, self).__init__(
            datatype,
            not field.writable,
            point_name,
            field.units,
            description=description,
        )

        self.name = field.name
        self.type = field.type
        self.default_value = self.get_default_value(field.type, default_value)

    def get_python_type(self, datatype):
        """
            Get python type from field data type

        :param datatype: register type

        :type datatype: str

        :return: python type
        """
        # Python 2.7 strings are byte arrays, this no longer works for 3.x
        if isinstance(datatype, tuple) and datatype[0] == "s":
            return str
        try:
            parse_struct = struct.Struct(datatype)
        except TypeError:
            parse_struct = struct.Struct(datatype[0])

        struct_types = [
            type(x)
            for x in parse_struct.unpack(("\x00" * parse_struct.size).encode("utf-8"))
        ]

        if len(struct_types) != 1:
            raise ValueError(
                "Invalid length Modbus Register for point {}".format(self.point_name)
            )
        return struct_types[0]

    def get_default_value(self, datatype, str_value):
        """
            Convert default value from str to the register type

        :param datatype: register type
        :param str_value: default value in str

        :type datatype: str
        :type str_value: str
        """
        python_type = self.get_python_type(datatype)
        if str_value:
            if python_type is int:
                return int(str_value)
            elif python_type is float:
                return float(str_value)
            elif python_type is bool:
                return helpers.str2bool(str_value)
            elif python_type is str:
                return str_value
            else:
                raise ValueError(
                    "Invalid data type for point {}: {}".format(
                        self.point_name, python_type
                    )
                )
        else:
            return None

    def get_state(self, modbus_client):
        """
            Read value of the register and return it

        :param modbus_client: the modbus tk client parsed from configure

        :type modbus_client: Client
        """
        state = getattr(modbus_client, self.name)
        return state.decode("utf-8") if isinstance(state, bytes) else state

    def set_state(self, modbus_client, value):
        """
            Set value for the register and return the actual value that is set

        :param modbus_client: the modbus tk client that is parsed from configure
        :param value: setting value for writable register

        :type modbus_client: Client
        :type value: same type as register type
        """
        setattr(modbus_client, self.name, value)
        modbus_client.write_all()

        return self.get_state(modbus_client)


class Interface(BasicRevert, BaseInterface):
    """
    Interface implementation of the ModbusTK Driver
    """

    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)
        self.name_map = dict()  # dictionary mapping the register name to point name
        self.modbus_client = None
        self.name = None  # name of the driver

    def configure(self, config: dict, registry_config: list):
        """
            Parse driver and csv config to define client transport, add registers to ModbusTKRegister,
            and set default values for revert reading

        :param config: dictionary of device configure
        :param registry_config: the list of all register dictionary parsed from the csv file

        :type config: dictionary
        :type registry_config: list
        """
        self.name = config.get("name", "UNKNOWN")

        self.check_ignored_config_keys(config)

        # Modbus client must be created before inserting registers into driver, which is done in self.parse_config()
        self.modbus_client = self.get_modubus_client(config, registry_config)

        self.parse_config(registry_config)

        _log.debug(f"Completed configuration for ModbusTK Driver: {self.name}")

    @classmethod
    def config_keys(cls):
        return [
            "name",
            "device_type",
            "device_address",
            "port",
            "slave_id",
            "baudrate",
            "bytesize",
            "parity",
            "stopbits",
            "xonxoff",
            "addressing",
            "endian",
            "write_multiple_registers",
            "register_map",
        ]

    def check_ignored_config_keys(self, config):
        ignored_config_keys = [k for k in config.keys() if k not in self.config_keys()]
        if ignored_config_keys:
            _log.warning(f"{self.name}, Ignored config : {ignored_config_keys}")

    @classmethod
    def parity(cls):
        return dict(none="N", even="E", odd="O", mark="M", space="S")

    def get_modubus_client(self, config, registry_config):
        # Parsing driver configurations from 'config'

        # Required driver configurations
        device_address = config["device_address"]

        # Optional driver configurations
        # 'name' has already been parsed in this Driver's constructor (see __init__) and added as a class attribute

        port = config.get("port", 0)
        slave_address = config.get("slave_id", 1)
        baudrate = config.get("baudrate", 9600)
        bytesize = config.get("bytesize", 8)  # valid values: 5, 6, 7, 8
        parity = self.parity()[config.get("parity", "none")]
        stopbits = config.get("stopbits", 1)  # valid values: 1, 1.5, 2
        xonxoff = config.get("xonxoff", 0)  # boolean
        addressing = config.get("addressing", helpers.OFFSET).lower()  # valid values: offset, offset_plus, or address
        endian = config.get("endian", "big")  # valid values: big, small

        x = config["write_multiple_registers"]
        _log.debug(f"write_multiple_registers config: {x}. The type is {type(x)}")
        write_single_values = (config.get("write_multiple_registers", True))

        modbus_client_class = Map(
            name=self.name,
            addressing=addressing,
            endian=endian,
            registry_config_lst=registry_config,
        ).get_class()

        modbus_client = modbus_client_class(
            device_address=device_address,
            port=port,
            slave_address=slave_address,
            write_single_values=write_single_values,
        )

        # Set modbus client transport based on device configure
        if port:
            _log.debug(f"Setting Modbus Client to TCP on port: {port}")
            modbus_client.set_transport_tcp(hostname=device_address, port=port)
        else:
            _log.debug(f"Setting ModbusClient to RTU transport on port {port} ")
            modbus_client.set_transport_rtu(
                device=device_address,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                xonxoff=xonxoff,
            )
        _log.info("Created ModbusClient.")

        return modbus_client

    def parse_config(self, registry_config: list):
        if not registry_config:
            _log.warning(f"Registry config is empty. This ModbusTK Driver for {self.name} will have no registers to read or write to.")
            return

        self.check_ignored_registry_config_keys(registry_config)
        registry_config = self.convert_modbus_registry(registry_config)

        for reg_dict in registry_config:
            register = ModbusTKRegister(
                reg_dict.get("Volttron Point Name"),
                reg_dict.get("Default Value", None),
                self.modbus_client.field_by_name(reg_dict.get("Register Name")),
            )
            self.insert_register(register)

            if not register.read_only and register.default_value:
                point_name = register.point_name
                default_value = register.default_value
                _log.debug(f"Setting default on register: {point_name, default_value}")
                self.set_default(point_name, default_value)

        _log.info("Finished setting up ModbusTK registers.")

    def convert_modbus_registry(self, registry_config: list):
        """Convert registry_config to new modbus_tk registry format if registry_config is in modbus csv format; otherwise return origin registry_config"""
        if registry_config and "Point Address" in registry_config[0]:
            _log.info("Converting registry config to new ModbusTK format.")
            new_registry_config_lst = []
            for reg_dict in registry_config:
                point_name = reg_dict.get("Volttron Point Name")
                register_name = (
                    reg_dict.get("Reference Point Name", point_name)
                    .replace(" ", "_")
                    .lower()
                )
                address = reg_dict.get("Point Address")
                datatype = reg_dict["Modbus Register"]

                unit = reg_dict.get("Units")
                writable = reg_dict.get("Writable")
                default_value = reg_dict.get("Default Value", None)
                description = reg_dict.get("Notes", "")
                mixed_endian = reg_dict.get("Mixed Endian", "False").lower()

                new_registry_config_lst.append(
                    {
                        "Volttron Point Name": point_name,
                        "Register Name": register_name,
                        "Address": address,
                        "Type": datatype,
                        "Units": unit,
                        "Writable": writable,
                        "Default Value": default_value,
                        "Mixed Endian": mixed_endian,
                        "Description": description,
                    }
                )

            return new_registry_config_lst
        return registry_config

    def insert_register(self, register):
        """
            Insert register into ModbusTKRegister

        :param register: register to add to the interface

        :type register: ModbusTKRegister
        """
        super(Interface, self).insert_register(register)
        self.name_map[register.name] = register.point_name

    @classmethod
    def registry_columns(cls):
        return [
            "Volttron Point Name",
            "Register Name",
            "Address",
            "Type",
            "Units",
            "Writable",
            "Default Value",
            "Transform",
            "Table",
            "Mixed Endian",
            "Description",
        ]

    def check_ignored_registry_config_keys(self, registry_config: list):
        ignored_registry_columns = set()
        for c in registry_config:
            for k in c.keys():
                if k not in self.registry_columns():
                    ignored_registry_columns.add(k)

        if ignored_registry_columns:
            _log.warning(
                f"{self.name}, Ignored registry config columns: {ignored_registry_columns}"
            )

    def get_point(self, point_name):
        """
            Get the value of a point from a device and return it

        :param point_name: register point name

        :type point_name: str
        """
        return self.get_register_by_name(point_name).get_state(self.modbus_client)

    def _set_point(self, point_name, value):
        """
            Set the value of a point on a device and ideally return the actual value set

        :param point_name: register point name
        :param value: setting value for writable register

        :type point_name: str
        :type value: same type as register type
        """
        return self.get_register_by_name(point_name).set_state(
            self.modbus_client, value
        )

    def _scrape_all(self):
        """Get a dictionary mapping point name to values of all defined registers"""
        return dict(
            (
                self.name_map[field.name],
                value.decode("utf-8") if isinstance(value, bytes) else value,
            )
            for field, value, timestamp in self.modbus_client.dump_all()
        )

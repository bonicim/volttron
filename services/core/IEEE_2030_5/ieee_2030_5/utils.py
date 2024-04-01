# -*- coding: utf-8 -*- {{{
# ===----------------------------------------------------------------------===
#
#                 Component of Eclipse VOLTTRON
#
# ===----------------------------------------------------------------------===
#
# Copyright 2023 Battelle Memorial Institute
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ===----------------------------------------------------------------------===
# }}}
def is_binary(binary: str) -> bool:
    return all([c in '01' for c in str(binary)])


def is_hex(hex: str) -> bool:
    return all([c in '0123456789ABCDEFabcdef' for c in hex])


def binary_to_binary_hex(binary: str) -> str:
    return hex(int(binary, 2))[2:]


def decimal_to_binary_hex(decimal: int) -> str:
    return hex(int(decimal))[2:]

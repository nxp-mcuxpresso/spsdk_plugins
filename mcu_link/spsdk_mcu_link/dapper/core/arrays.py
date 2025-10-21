#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024-2025 NXP
# Copyright 2025 Oidis
#
# SPDX-License-Identifier: BSD-3-Clause
"""Arrays implementation."""

import ctypes
from typing import Any, Optional, Union


class Uint8Array:
    """8-bit unsigned integer array implementation."""

    def __init__(
        self,
        source: Union[ctypes.Array, "Uint8Array"],
        offset: int = 0,
        length: Optional[int] = None,
    ) -> None:
        """8-bit unsigned integer array implementation.

        :param source: Source array to create from
        :param offset: Starting offset in the source array, defaults to 0
        :param length: Length of the array to create, defaults to None
        :raises TypeError: If source is not a valid array type
        :raises ValueError: If offset or length are invalid
        """
        if not isinstance(source, (ctypes.Array, Uint8Array)):
            raise TypeError("Source needs to be a ctype array")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("Offset needs to be a positive integer")
        if length is None:
            length = len(source) - offset
        elif not isinstance(length, int) or length < 0:
            raise ValueError("Length needs to be a positive integer")

        if offset + length > len(source):
            raise ValueError("Offset and length exceeds input source buffer size")

        self.length = length
        self.buffer: ctypes.Array
        if isinstance(source, Uint8Array):
            self.buffer = (ctypes.c_ubyte * length).from_buffer(source.buffer, offset)
        else:
            self.buffer = (ctypes.c_ubyte * length).from_buffer(source, offset)

    @property
    def length(self) -> int:
        """Get length of array.

        :return: Array length
        """
        return self._length

    @length.setter
    def length(self, value: int) -> None:
        """Set length of array.

        :param value: New array length
        """
        self._length = value

    # JS emulation
    def constructor(
        self, val: Union[ctypes.Array, "Uint8Array"], ptr: int, size: int
    ) -> "Uint8Array":
        """Create new array from existing array.

        :param val: Source array
        :param ptr: Starting offset
        :param size: Size of new array
        :return: New Uint8Array instance
        """
        n_array = Uint8Array(val, ptr, size)
        return n_array

    def set(self, source: "Uint8Array") -> int:
        """Copy data from source array.

        :param source: Source array to copy from
        :return: Length of array after copy
        """
        length_to_copy = min(self.length, len(source.buffer))
        ctypes.memmove(self.buffer, source.buffer, length_to_copy)
        return self.length

    def __getitem__(self, index: Union[str, int]) -> Any:
        """Get item from array by index or property name.

        :param index: Array index or property name
        :return: Value at index or property value
        :raises IndexError: If index is out of range or undefined
        """
        if index == "length":
            return self.length
        if index == "buffer":
            return self.buffer
        if index == "constructor":
            return self.constructor
        if index == "set":
            return self.set
        if index == "ptr":
            return ctypes.addressof(self.buffer)
        if isinstance(index, int):
            if index < 0 or index >= self.length:
                raise IndexError("Index out of range")
            return self.buffer[index]
        raise IndexError("Index out of range or undefined")

    def __setitem__(self, index: int, value: int) -> None:
        """Set value at specified index.

        :param index: Array index
        :param value: Value to set
        :raises IndexError: If index is out of range
        """
        if index < 0 or index >= self.length:
            raise IndexError("Index out of range")
        self.buffer[index] = value

    def __len__(self) -> int:
        """Get length of array.

        :return: Array length
        """
        return self.length

    def __repr__(self) -> str:
        """Get string representation of array.

        :return: String representation
        """
        return f"Uint8Array({self.length})"


class Int32Array:
    """32-bit integer array implementation."""

    def __init__(
        self,
        source: Union[ctypes.Array, Uint8Array, "Int32Array"],
        offset: int = 0,
        length: Optional[int] = None,
    ) -> None:
        """Initialize Int32Array.

        :param source: Source array to initialize from (ctypes.Array, Uint8Array, Int32Array)
        :param offset: Starting offset in source array, defaults to 0
        :param length: Number of elements to include, defaults to None (entire source array)
        :raises TypeError: If source is not a valid array type
        :raises ValueError: If offset is not a positive integer
        :raises ValueError: If length is not a positive integer
        :raises ValueError: If offset + length exceeds source buffer size
        """
        if not isinstance(source, (ctypes.Array, Int32Array, Uint8Array)):
            raise TypeError("Source needs to be a ctype array")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("Offset needs to be a positive integer")
        if length is None:
            length = len(source) - offset
        elif not isinstance(length, int) or length < 0:
            raise ValueError("Length needs to be a positive integer")

        if offset + length > len(source):
            raise ValueError("Offset and length exceeds input source buffer size")

        self.length = length
        self.buffer: ctypes.Array
        if isinstance(source, Uint8Array):
            self.buffer = (ctypes.c_int32 * length).from_buffer(source.buffer, offset)
        elif isinstance(source, Int32Array):
            self.buffer = (ctypes.c_int32 * length).from_buffer(source.buffer, offset)
        else:
            self.buffer = (ctypes.c_int32 * length).from_buffer(source, offset)

    @property
    def length(self) -> int:
        """Get length of array.

        :return: Length of array
        """
        return self._length

    @length.setter
    def length(self, value: int) -> None:
        """Set length of array.

        :param value: Length of array to set
        """
        self._length = value

    # JS emulation
    def constructor(
        self, val: Union[ctypes.Array, "Int32Array"], ptr: int, size: int
    ) -> "Int32Array":
        """Constructor method for creating a new Int32Array.

        :param val: Source array to initialize from (ctypes.Array, Int32Array)
        :param ptr: Starting offset in source array
        :param size: Number of elements to include
        :return: New Int32Array instance
        """
        n_array = Int32Array(val, ptr, size)
        return n_array

    def set(self, source: "Int32Array") -> int:
        """Set values from source array.

        :param source: Source Int32Array to copy values from
        :return: Length of array
        """
        length_to_copy = min(self.length, len(source.buffer))
        ctypes.memmove(self.buffer, source.buffer, length_to_copy)
        return self.length

    def __getitem__(self, index: Union[str, int]) -> Any:
        """Get item from array by index or property name.

        :param index: Index or property name to access
        :raises IndexError: If numeric index is out of range
        :raises IndexError: If property name is not valid
        :return: Value at index or property value
        """
        if index == "length":
            return self.length
        if index == "buffer":
            return self.buffer
        if index == "constructor":
            return self.constructor
        if index == "set":
            return self.set
        if index == "ptr":
            # return f"{ctypes.addressof(self.buffer)}"
            return ctypes.addressof(self.buffer)
        if isinstance(index, int):
            if index < 0 or index >= self.length:
                raise IndexError("Index out of range")
            return self.buffer[index]
        raise IndexError("Index out of range or undefined")

    def __setitem__(self, index: int, value: int) -> None:
        """Set item in array at index.

        :param index: Array index to set
        :param value: Integer value to set at index
        :raises IndexError: If index is out of range
        """
        if index < 0 or index >= self.length:
            raise IndexError("Index out of range")
        self.buffer[index] = value

    def __len__(self) -> int:
        """Return length of array.

        :return: Length of array
        """
        return self.length

    def __repr__(self) -> str:
        """Return string representation of array.

        :return: String representation of array
        """
        return f"Int32Array({self.length})"

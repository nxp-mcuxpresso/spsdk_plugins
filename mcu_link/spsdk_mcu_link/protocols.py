#!/usr/bin/env python
#
# Copyright 2026 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Debug probe protocol compatibility helpers."""

import warnings
from enum import Enum
from typing import Any

import spsdk
from spsdk.debuggers import debug_probe as spsdk_debug_probe
from spsdk.debuggers.debug_probe import SPSDKDebugProbeError

if str(getattr(spsdk, "__version__", "")).startswith("4."):
    warnings.warn(
        "The local debug probe protocol compatibility hack must be removed for SPSDK 4.x.",
        RuntimeWarning,
        stacklevel=2,
    )


class DebugProbeProtocol(Enum):
    """Local protocol copy for compatibility with older SPSDK versions."""

    SWD = "swd"
    JTAG = "jtag"
    ONCE = "once"

    @property
    def label(self) -> str:
        """Protocol label."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Compare protocol by label across SPSDK and plugin-local enum copies."""
        return self.label == getattr(other, "label", str(other))

    def __hash__(self) -> int:
        """Return hash compatible with label-based equality."""
        return hash(self.label)

    @classmethod
    def labels(cls) -> list[str]:
        """Return supported protocol labels."""
        return [protocol.label for protocol in cls]

    @classmethod
    def from_label(cls, label: str) -> "DebugProbeProtocol":
        """Create protocol from label."""
        for protocol in cls:
            if protocol.label == label:
                return protocol
        raise ValueError(label)


if (
    SpsdkProtocolEnum := getattr(spsdk_debug_probe, "DebugProbeProtocol", None)
) is not None and any(
    (
        SpsdkProtocolEnum.SWD.label != DebugProbeProtocol.SWD.label,
        SpsdkProtocolEnum.JTAG.label != DebugProbeProtocol.JTAG.label,
        SpsdkProtocolEnum.ONCE.label != DebugProbeProtocol.ONCE.label,
    )
):
    raise SPSDKDebugProbeError("Incompatible SPSDK debug probe protocol labels.")


def get_debug_probe_protocol(probe: Any) -> DebugProbeProtocol:
    """Get requested debug probe protocol across old and new SPSDK versions.

    :param probe: Debug probe instance.
    :return: Requested protocol, defaulting to the first supported protocol.
    :raises SPSDKDebugProbeError: Invalid or unsupported protocol has been requested.
    """
    options = getattr(probe, "options", {}) or {}
    protocol = getattr(probe, "protocol", None) or options.get("protocol")
    if protocol is None and options.get("use_jtag") is not None:
        protocol = DebugProbeProtocol.JTAG.label
    if protocol is None:
        return probe.SUPPORTED_PROTOCOLS[0]
    if isinstance(protocol, DebugProbeProtocol):
        requested_protocol = protocol
    else:
        label = getattr(protocol, "label", str(protocol))
        try:
            requested_protocol = DebugProbeProtocol.from_label(label)
        except (ValueError, KeyError) as exc:
            raise SPSDKDebugProbeError(
                f"Unsupported debug probe protocol '{protocol}'. "
                f"Supported protocols: {', '.join(DebugProbeProtocol.labels())}."
            ) from exc

    if requested_protocol not in probe.SUPPORTED_PROTOCOLS:
        raise SPSDKDebugProbeError(
            f"Debug probe '{probe.NAME}' does not support {requested_protocol.label.upper()} protocol."
        )
    return requested_protocol

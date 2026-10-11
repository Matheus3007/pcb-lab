"""Circuit description: parts pinned by LCSC ID, pins -> nets, net classes, assertions.

Board files (`boards/<name>/circuit.py`) define `circuit()` returning a Circuit. Nothing
here imports pcbnew; the circuit is serialized to build/netlist.json for later stages.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import yaml

LIB = Path(__file__).resolve().parents[2] / "lib"


class CircuitError(Exception):
    pass


# Generic passives: KiCad stock footprints, two pins, LCSC ID given per instance.
_PASSIVE_FP = {
    "R": "Resistor_SMD:R_{size}_{metric}Metric",
    "C": "Capacitor_SMD:C_{size}_{metric}Metric",
    "LED": "LED_SMD:LED_{size}_{metric}Metric",
}
_METRIC = {"0201": "0603", "0402": "1005", "0603": "1608", "0805": "2012", "1206": "3216"}


def _load_library() -> dict:
    return yaml.safe_load((LIB / "parts.yaml").read_text()) or {}


@dataclass(frozen=True)
class Pin:
    part: "Part"
    name: str

    @property
    def pads(self) -> list[str]:
        return self.part.pins[self.name]

    def __repr__(self) -> str:
        return f"{self.part.ref}.{self.name}"


@dataclass(eq=False)
class Part:
    ref: str
    footprint: str                 # "Lib:Name"
    value: str
    lcsc: str | None
    pins: dict[str, list[str]]     # pin name -> pad numbers
    mpn: str | None = None
    dnp: bool = False              # do not populate (not assembled by JLC)
    meta: dict = field(default_factory=dict)
    block: str | None = None       # functional block (schematic grouping), set by `with c.block(...)`

    def __getitem__(self, name: str) -> Pin:
        if name not in self.pins:
            raise CircuitError(f"{self.ref} has no pin {name!r} (has {sorted(self.pins)})")
        return Pin(self, name)

    def __getattr__(self, name: str) -> Pin:
        if name.startswith("_") or name not in self.__dict__.get("pins", {}):
            raise AttributeError(name)
        return Pin(self, name)


@dataclass(eq=False)
class Net:
    name: str
    pins: list[Pin] = field(default_factory=list)
    net_class: str = "Default"

    def __iadd__(self, pin: Pin) -> "Net":
        self.pins.append(pin)
        return self


@dataclass
class NetClass:
    name: str
    track_width: float             # mm
    clearance: float               # mm
    via_diameter: float = 0.6
    via_drill: float = 0.3
    current_a: float | None = None  # continuous current the class must carry


class Circuit:
    def __init__(self, name: str):
        self.name = name
        self.parts: dict[str, Part] = {}
        self.nets: dict[str, Net] = {}
        self.no_connect: set[tuple[str, str]] = set()
        self.net_classes: dict[str, NetClass] = {}
        self.assertions: list[dict] = []
        self.power_flags: list[str] = []
        self._block: str | None = None
        self._lib = _load_library()

    @contextmanager
    def block(self, name: str):
        """Group the parts created inside: one framed block per group in the generated schematic."""
        prev, self._block = self._block, name
        try:
            yield
        finally:
            self._block = prev

    # -- parts ---------------------------------------------------------------
    def part(self, ref: str, key: str, value: str | None = None, dnp: bool = False) -> Part:
        """Add a part defined in lib/parts.yaml."""
        if key not in self._lib:
            raise CircuitError(f"{key!r} not in lib/parts.yaml")
        d = self._lib[key]
        pins = {k: [str(p) for p in (v if isinstance(v, list) else [v])] for k, v in d["pins"].items()}
        p = Part(ref, d["footprint"], value or d.get("value", key), d.get("lcsc"), pins,
                 mpn=d.get("mpn", key), dnp=dnp or d.get("dnp", False), meta={"lib_key": key, **d})
        return self._add(p)

    def passive(self, ref: str, kind: str, value: str, size: str, lcsc: str, dnp: bool = False) -> Part:
        """Two-pin R / C / LED with a KiCad stock footprint. LED pins are K and A."""
        fp = _PASSIVE_FP[kind].format(size=size, metric=_METRIC[size])
        pins = {"K": ["1"], "A": ["2"]} if kind == "LED" else {"1": ["1"], "2": ["2"]}
        return self._add(Part(ref, fp, value, lcsc, pins, dnp=dnp, meta={"kind": kind, "size": size}))

    def _add(self, p: Part) -> Part:
        if p.ref in self.parts:
            raise CircuitError(f"duplicate ref {p.ref}")
        p.block = self._block
        self.parts[p.ref] = p
        return p

    # -- nets ----------------------------------------------------------------
    def net(self, name: str) -> Net:
        return self.nets.setdefault(name, Net(name))

    def connect(self, name: str, *pins: Pin) -> Net:
        n = self.net(name)
        for pin in pins:
            n += pin
        return n

    def nc(self, *pins: Pin) -> None:
        """Mark pins as intentionally unconnected."""
        for pin in pins:
            self.no_connect.add((pin.part.ref, pin.name))

    def power_flag(self, *net_names: str) -> None:
        """Declare nets powered from off the board (a connector, a battery). KiCad's ERC requires every
        power-input pin to be driven; this is the honest way to say "driven externally"."""
        for n in net_names:
            if n not in self.power_flags:
                self.power_flags.append(n)

    def net_class(self, nc: NetClass, *net_names: str) -> None:
        self.net_classes[nc.name] = nc
        for n in net_names:
            self.net(n).net_class = nc.name

    # -- design intent -------------------------------------------------------
    def check(self, name: str, value: float, lo: float, hi: float, unit: str = "") -> None:
        """Record a numeric design assertion, e.g. LED current within limits."""
        self.assertions.append({"name": name, "value": value, "min": lo, "max": hi,
                                "unit": unit, "ok": lo <= value <= hi})

    # -- validation ----------------------------------------------------------
    def validate(self) -> list[dict]:
        """Electrical sanity checks (our stand-in for ERC). Returns issues."""
        issues = []
        where: dict[tuple[str, str], str] = {}
        for net in self.nets.values():
            for pin in net.pins:
                key = (pin.part.ref, pin.name)
                if key in where and where[key] != net.name:
                    issues.append({"severity": "error", "check": "pin_on_two_nets",
                                   "msg": f"{pin} on {where[key]} and {net.name}"})
                where[key] = net.name
                if key in self.no_connect:
                    issues.append({"severity": "error", "check": "nc_pin_connected",
                                   "msg": f"{pin} is marked NC but is on {net.name}"})
            if len({(p.part.ref, p.name) for p in net.pins}) < 2:
                issues.append({"severity": "error", "check": "single_pin_net",
                               "msg": f"net {net.name} has fewer than 2 pins"})
        for part in self.parts.values():
            for pin in part.pins:
                if (part.ref, pin) not in where and (part.ref, pin) not in self.no_connect:
                    issues.append({"severity": "error", "check": "unconnected_pin",
                                   "msg": f"{part.ref}.{pin} is neither connected nor marked NC"})
            if not part.lcsc and not part.dnp:
                issues.append({"severity": "error", "check": "no_lcsc",
                               "msg": f"{part.ref} is assembled but has no LCSC ID"})
        for n in self.power_flags:
            if n not in self.nets:
                issues.append({"severity": "error", "check": "power_flag_unknown_net",
                               "msg": f"power_flag({n!r}): no such net"})
        for a in self.assertions:
            if not a["ok"]:
                issues.append({"severity": "error", "check": "assertion",
                               "msg": f"{a['name']} = {a['value']:.4g}{a['unit']} not in "
                                      f"[{a['min']:.4g}, {a['max']:.4g}]"})
        return issues

    # -- export --------------------------------------------------------------
    def pad_nets(self, ref: str) -> dict[str, str]:
        out = {}
        for net in self.nets.values():
            for pin in net.pins:
                if pin.part.ref == ref:
                    for pad in pin.pads:
                        out[pad] = net.name
        return out

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parts": [{
                "ref": p.ref, "footprint": p.footprint, "value": p.value, "lcsc": p.lcsc,
                "mpn": p.mpn, "dnp": p.dnp, "block": p.block, "pins": p.pins, "pad_nets": self.pad_nets(p.ref),
                "meta": {k: v for k, v in p.meta.items() if k not in ("pins",)},
            } for p in self.parts.values()],
            "nets": {n.name: {"class": n.net_class, "pins": [repr(p) for p in n.pins]}
                     for n in self.nets.values()},
            "no_connect": sorted(f"{r}.{p}" for r, p in self.no_connect),
            "net_classes": {k: vars(v) for k, v in self.net_classes.items()},
            "assertions": self.assertions,
            "power_flags": self.power_flags,
        }

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=1, default=str) + "\n")

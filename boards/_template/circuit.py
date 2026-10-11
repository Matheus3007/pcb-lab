"""<board>: one-line purpose. See spec.md."""
from pcbkit.circuit import Circuit, NetClass


def circuit() -> Circuit:
    c = Circuit("<board>")
    # with c.block("3.3V regulator"):          # one framed group in the generated schematic
    #     u1 = c.part("U1", "<lib/parts.yaml key>")
    #     r1 = c.passive("R1", "R", "10k", "0402", lcsc="C25744")
    # c.power_flag("VBAT", "GND")               # nets supplied from off the board (ERC)
    # c.connect("3V3", u1.VDD, r1["1"])
    # c.nc(u1.NC1)
    # c.net_class(NetClass("Power", track_width=0.4, clearance=0.2, current_a=0.5), "3V3", "GND")
    # c.check("LED current", (3.3 - 2.0) / 1000, 0.5e-3, 5e-3, "A")
    return c

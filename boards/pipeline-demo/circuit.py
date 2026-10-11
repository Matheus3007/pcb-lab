"""pipeline-demo: USB-C 5 V in -> XC6206 3.3 V LDO -> status LED + 4-pin header.

Phase 0 throwaway board to prove the pipeline. Not meant to be ordered.
"""
from pcbkit.circuit import Circuit, NetClass


def circuit() -> Circuit:
    c = Circuit("pipeline-demo")

    # --- USB-C power-only sink -------------------------------------------
    j1 = c.part("J1", "TYPE-C-31-M-12")
    r1 = c.passive("R1", "R", "5.1k", "0402", lcsc="C25905")   # CC1 Rd
    r2 = c.passive("R2", "R", "5.1k", "0402", lcsc="C25905")   # CC2 Rd
    c.connect("VBUS", j1.VBUS)
    c.connect("GND", j1.GND, j1.SHIELD)
    c.connect("CC1", j1.CC1, r1["1"])
    c.connect("CC2", j1.CC2, r2["1"])
    c.connect("GND", r1["2"], r2["2"])
    c.nc(j1.DP1, j1.DN1, j1.DP2, j1.DN2, j1.SBU1, j1.SBU2)

    # --- 3.3 V LDO --------------------------------------------------------
    u1 = c.part("U1", "XC6206P332MR-G")
    c1 = c.passive("C1", "C", "1uF", "0402", lcsc="C52923")    # input
    c2 = c.passive("C2", "C", "1uF", "0402", lcsc="C52923")    # output (datasheet: 1 uF)
    c3 = c.passive("C3", "C", "10uF", "0603", lcsc="C19702")   # bulk on 3V3
    c.connect("VBUS", u1.VIN, c1["1"])
    c.connect("3V3", u1.VOUT, c2["1"], c3["1"])
    c.connect("GND", u1.VSS, c1["2"], c2["2"], c3["2"])

    # --- status LED -------------------------------------------------------
    r3 = c.passive("R3", "R", "1k", "0402", lcsc="C11702")
    d1 = c.passive("D1", "LED", "red", "0603", lcsc="C2286")
    c.connect("3V3", r3["1"])
    c.connect("LED_A", r3["2"], d1.A)
    c.connect("GND", d1.K)

    # --- header (not assembled) + mounting hole ---------------------------
    j2 = c.part("J2", "PinHeader_1x04")
    c.connect("VBUS", j2["1"])
    c.connect("3V3", j2["2"])
    c.connect("GND", j2["3"], j2["4"])
    c.part("H1", "MountingHole_M2")

    # --- net classes ------------------------------------------------------
    c.net_class(NetClass("Power", track_width=0.4, clearance=0.2, current_a=0.2),
                "VBUS", "3V3", "GND")

    # --- design intent ----------------------------------------------------
    vbus_max, vout = 5.25, 3.3
    for vf in (1.8, 2.4):  # KT-0603R Vf range from JLC listing
        c.check(f"LED current @Vf={vf}V", (vout - vf) / 1000, 0.5e-3, 5e-3, "A")
    c.check("LDO input max vs XC6206 6.0V rating", vbus_max, 0, 6.0, "V")
    i_budget = 0.100  # header load budget
    c.check("LDO dissipation @100mA, Vin=5.25V", (vbus_max - vout) * i_budget, 0, 0.25, "W")
    return c

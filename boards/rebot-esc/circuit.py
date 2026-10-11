"""rebot-esc: plug-in AM32 drive-ESC module for Rebot. See spec.md.

One sensorless BLDC channel: AT32F421 (stock AM32 target OPENESC_20_F421, HARDWARE_GROUP_AT_B pin map)
-> DRV8300D three-phase gate driver -> 6x HSBB6066 60 V MOSFETs. Everything reaches the carrier through
one 2x10 header. The channel topology (BEMF network, gate resistors, bootstrap caps, MCU support parts)
follows incutec OpenESC-20x20 rev3.3 (CERN-OHL-S-2.0), see docs/projects/battlebot-esc-research.md.
"""
from pcbkit.circuit import Circuit, NetClass

# Basic passives (lib/basic_passives.yaml + JLC Basic lookups 2026-10-11)
R10, R220, R1K, R10K = "C25077", "C25091", "C11702", "C25744"   # 0402 thick film 1%
C100N_50V = "C307331"     # 100 nF 50 V X7R 0402
C1U_25V = "C52923"        # 1 uF 25 V X5R 0402
C1U_50V = "C15849"        # 1 uF 50 V X5R 0603
C10U_25V = "C15850"       # 10 uF 25 V X5R 0805
C10U_50V = "C440198"      # 10 uF 50 V X5R 0805

PHASES = ("A", "B", "C")


def circuit() -> Circuit:
    c = Circuit("rebot-esc")

    # --- header: the only connection to the carrier -------------------------------------------
    # 2x10, keyed: position 7 has no pin on the module and a blocked hole in the carrier's socket, so a
    # module rotated 180 deg (pin n -> socket 21-n) can't go in: its pin 14 hits the blocked hole.
    # Without the key a rotated module would short the battery through the high-side body diode of
    # phase C, a motor winding and a low-side body diode (traced 2026-10-11), so the key is required.
    with c.block("Carrier header (2x10, hand-soldered)"):
        j1 = c.part("J1", "PinHeader_2x10")
        c.part("H1", "MountingHole_M2")   # retention screw, no current
    c.connect("VBAT", j1["1"], j1["2"], j1["3"])
    c.connect("GND", j1["4"], j1["5"], j1["6"])
    c.nc(j1["7"])                          # KEY: pin pulled from the header, socket hole blocked
    c.connect("12V", j1["8"])
    c.connect("DSHOT", j1["9"])
    c.connect("SWDIO", j1["10"])
    c.connect("SWCLK", j1["11"])
    c.connect("PH_A", j1["12"], j1["13"], j1["14"])
    c.connect("PH_B", j1["15"], j1["16"], j1["17"])
    c.connect("PH_C", j1["18"], j1["19"], j1["20"])
    c.power_flag("VBAT", "GND", "12V")   # all supplied by the carrier

    # --- VBAT bulk / HF decoupling at the half bridges ----------------------------------------
    with c.block("VBAT decoupling"):
        bulk = [c.passive(f"C{i}", "C", "10uF", "0805", lcsc=C10U_50V) for i in (1, 2, 3)]
        hf = [c.passive(f"C{i}", "C", "100nF", "0402", lcsc=C100N_50V) for i in (4, 5, 6)]
    for cap in bulk + hf:
        c.connect("VBAT", cap["1"])
        c.connect("GND", cap["2"])

    # --- 3.3 V for the MCU, from the carrier's 12 V gate rail --------------------------------
    with c.block("3.3V LDO (from 12V)"):
        u3 = c.part("U3", "HT7533-1")
        c7 = c.passive("C7", "C", "1uF", "0603", lcsc=C1U_50V)    # LDO in
        c8 = c.passive("C8", "C", "1uF", "0402", lcsc=C1U_25V)    # LDO out
    c.connect("12V", u3.VIN, c7["1"])
    c.connect("3V3", u3.VOUT, c8["1"])
    c.connect("GND", u3.GND, c7["2"], c8["2"])

    # --- MCU (AM32) ---------------------------------------------------------------------------
    with c.block("MCU AT32F421 (AM32)"):
        u1 = c.part("U1", "AT32F421G8U7")
        c9 = c.passive("C9", "C", "100nF", "0402", lcsc=C100N_50V)   # VDD
        r1 = c.passive("R1", "R", "10", "0402", lcsc=R10)              # VDDA filter
        c10 = c.passive("C10", "C", "100nF", "0402", lcsc=C100N_50V)  # VDDA
        r2 = c.passive("R2", "R", "10k", "0402", lcsc=R10K)            # NRST pull-up
        c11 = c.passive("C11", "C", "100nF", "0402", lcsc=C100N_50V)  # NRST
        r3 = c.passive("R3", "R", "10k", "0402", lcsc=R10K)            # BOOT0 pull-down
        r4 = c.passive("R4", "R", "220", "0402", lcsc=R220)            # DShot series
    c.connect("3V3", u1.VDD, c9["1"], r1["1"], r2["1"])
    c.connect("VDDA", r1["2"], u1.VDDA, c10["1"])
    c.power_flag("VDDA")   # fed from 3V3 through the R1 filter, which ERC can't see as a source
    c.connect("NRST", u1.NRST, r2["2"], c11["1"])
    c.connect("BOOT0", u1.BOOT0, r3["1"])
    c.connect("GND", u1.VSS, u1.EP, c9["2"], c10["2"], c11["2"], r3["2"])
    c.connect("DSHOT", r4["1"])
    c.connect("DSHOT_MCU", r4["2"], u1.PB4)          # TMR3_CH1 input capture
    c.connect("SWDIO", u1.PA13)
    c.connect("SWCLK", u1.PA14)
    c.nc(u1.PA2, u1.PA3, u1.PA6, u1.PA15, u1.PB3, u1.PB5, u1.PB6, u1.PB7, u1.PF0, u1.PF1)

    # AM32 HARDWARE_GROUP_AT_B: (low pin, high pin) per phase
    pwm = {"A": (u1.PB1, u1.PA10), "B": (u1.PB0, u1.PA9), "C": (u1.PA7, u1.PA8)}
    bemf_pin = {"A": u1.PA0, "B": u1.PA4, "C": u1.PA5}

    # --- gate driver --------------------------------------------------------------------------
    with c.block("Gate driver DRV8300D"):
        u2 = c.part("U2", "DRV8300DRGER")
        c12 = c.passive("C12", "C", "10uF", "0805", lcsc=C10U_25V)    # GVDD bulk (>=10 uF)
        c13 = c.passive("C13", "C", "100nF", "0402", lcsc=C100N_50V)  # GVDD HF
        cboot = {p: c.passive(f"C{14 + i}", "C", "100nF", "0402", lcsc=C100N_50V)
                 for i, p in enumerate(PHASES)}
    c.connect("12V", u2.GVDD, c12["1"], c13["1"])
    c.connect("GND", u2.GND, u2.EP, c12["2"], c13["2"])
    c.nc(u2.MODE, u2.DT, u2.NC1, u2.NC2)   # MODE float = non-inverted INLx; DT float = fixed dead time
    for p in PHASES:
        lo, hi = pwm[p]
        c.connect(f"INL_{p}", lo, u2[f"INL{p}"])
        c.connect(f"INH_{p}", hi, u2[f"INH{p}"])
        c.connect(f"BST_{p}", u2[f"BST{p}"], cboot[p]["1"])
        c.connect(f"PH_{p}", u2[f"SH{p}"], cboot[p]["2"])

    # --- power stage: one half bridge per phase -----------------------------------------------
    q = 1
    for i, p in enumerate(PHASES):
        with c.block(f"Half bridge {p}"):
            qh = c.part(f"Q{q}", "HSBB6066")
            ql = c.part(f"Q{q + 1}", "HSBB6066")
            rgh = c.passive(f"R{5 + 2 * i}", "R", "10", "0402", lcsc=R10)   # gate resistors
            rgl = c.passive(f"R{6 + 2 * i}", "R", "10", "0402", lcsc=R10)
        q += 2
        c.connect("VBAT", qh.D)
        c.connect(f"PH_{p}", qh.S, ql.D)
        c.connect("GND", ql.S)
        c.connect(f"GH_{p}", u2[f"GH{p}"], rgh["1"])
        c.connect(f"GH_{p}_Q", rgh["2"], qh.G)
        c.connect(f"GL_{p}", u2[f"GL{p}"], rgl["1"])
        c.connect(f"GL_{p}_Q", rgl["2"], ql.G)

    # --- BEMF sensing: 10k/1k divider per phase + 10k star to a virtual neutral --------------
    with c.block("BEMF sense network"):
        r = 11
        for p in PHASES:
            top = c.passive(f"R{r}", "R", "10k", "0402", lcsc=R10K)
            bot = c.passive(f"R{r + 1}", "R", "1k", "0402", lcsc=R1K)
            star = c.passive(f"R{r + 2}", "R", "10k", "0402", lcsc=R10K)
            r += 3
            c.connect(f"PH_{p}", top["1"])
            c.connect(f"FB_{p}", top["2"], bot["1"], star["1"], bemf_pin[p])
            c.connect("GND", bot["2"])
            c.connect("FB_COMMON", star["2"])
    c.connect("FB_COMMON", u1.PA1)

    # --- net classes --------------------------------------------------------------------------
    c.net_class(NetClass("Power", track_width=1.0, clearance=0.2, current_a=10.0),
                "VBAT", "GND", "PH_A", "PH_B", "PH_C")
    c.net_class(NetClass("Gate", track_width=0.3, clearance=0.15, current_a=1.0),
                "12V", *(f"{k}_{p}{s}" for k in ("GH", "GL") for p in PHASES for s in ("", "_Q")),
                *(f"BST_{p}" for p in PHASES))

    # --- design intent --------------------------------------------------------------------------
    vbat_max = 26.1          # 6S LiHV, 4.35 V/cell
    vbat_spike = 40.0        # assumed regen/brake transient budget
    v_gvdd = 12.0
    c.check("MOSFET Vds: spike budget vs 60 V rating", vbat_spike, 0, 60 * 0.8, "V")
    c.check("BEMF divider at full LiHV vs 3.3 V MCU", vbat_max * 1 / 11, 0, 3.3, "V")
    c.check("BEMF clamp current at spike (10k series)", (vbat_spike - 3.6) / 10e3, 0, 5e-3, "A")
    c.check("GVDD within DRV8300 4.8-20 V", v_gvdd, 4.8, 20, "V")
    c.check("Gate 12 V vs MOSFET Vgs +-20 V", v_gvdd, 0, 20, "V")
    c.check("Bootstrap droop: Qg 33 nC / 100 nF", 33e-9 / 100e-9, 0, 1.0, "V")
    c.check("GVDD cap >= 10x bootstrap cap", 10e-6 / 100e-9, 10, 1e6, "x")
    c.check("HT7533 Vin vs 30 V rating", v_gvdd, 3.5, 30, "V")
    c.check("HT7533 dissipation @30 mA (SOT-89 0.5 W)", (v_gvdd - 3.3) * 0.030, 0, 0.5, "W")
    c.check("Jig flash: ST-LINK 5 V into the 12 V pin keeps 3V3 in regulation", 5.0 - 3.3, 0.1, 30, "V")
    return c

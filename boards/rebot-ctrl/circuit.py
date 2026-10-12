"""rebot-ctrl: mini controller for Rebot. See spec.md.

ELRS receiver (CRSF) -> STM32G431 (+ LSM6DSV32X gyro, 16 MB log flash, USB) -> DShot x4 -> 4-in-1 AM32 ESC.
Powers itself and the receiver from the ESC connector's battery pin through a 65 V buck.
"""
from pcbkit.circuit import Circuit, NetClass

# Basic passives (lib/basic_passives.yaml + JLC Basic lookups 2026-10-11)
R100, R1K, R5K1, R10K, R22K, R100K = "C25076", "C11702", "C25905", "C25744", "C25768", "C25741"   # 0402 1%
C10N, C100N, C1U, C4U7 = "C15195", "C307331", "C52923", "C23733"   # 0402: 10nF 50V, 100nF 50V, 1uF 25V, 4.7uF 10V
C1U_50V_0603 = "C15849"
C2U2_50V = "C377773"     # 0805
C22U_25V = "C45783"      # 0805


def circuit() -> Circuit:
    c = Circuit("rebot-ctrl")

    # --- connectors ----------------------------------------------------------------------------
    with c.block("ESC connector (JST-SH 8P, G V 1 2 3 4 C T)"):
        j1 = c.part("J1", "SM08B-SRSS-TB")
    c.connect("GND", j1["1"], j1.MP)
    c.connect("VBAT", j1["2"])
    for k in range(4):
        c.connect(f"M{k + 1}", j1[str(3 + k)])
    c.connect("ESC_CURR", j1["7"])
    c.connect("ESC_TLM", j1["8"])
    c.power_flag("VBAT", "GND")   # battery, through the ESC's 8-pin cable

    with c.block("Receiver connector (JST-GH 4P, CRSF)"):
        j2 = c.part("J2", "SM04B-GHS-TB")
        r_rx = c.passive("R1", "R", "100", "0402", lcsc=R100)
        r_tx = c.passive("R2", "R", "100", "0402", lcsc=R100)
    c.connect("+5V", j2["1"])
    c.connect("GND", j2["2"], j2.MP)
    c.connect("CRSF_IN", j2["3"], r_rx["1"])     # receiver TX
    c.connect("CRSF_OUT", j2["4"], r_tx["1"])    # receiver RX

    with c.block("USB-C (device)"):
        j3 = c.part("J3", "TYPE-C-31-M-12")
        r_cc1 = c.passive("R3", "R", "5.1k", "0402", lcsc=R5K1)
        r_cc2 = c.passive("R4", "R", "5.1k", "0402", lcsc=R5K1)
        d2 = c.part("D2", "B5819WS")          # SOD-323: USB bench current only
    c.connect("VBUS", j3.VBUS, d2.A)
    c.connect("GND", j3.GND, j3.SHIELD, r_cc1["2"], r_cc2["2"])
    c.connect("CC1", j3.CC1, r_cc1["1"])
    c.connect("CC2", j3.CC2, r_cc2["1"])
    c.connect("USB_DP", j3.DP1, j3.DP2)
    c.connect("USB_DM", j3.DN1, j3.DN2)
    c.nc(j3.SBU1, j3.SBU2)
    c.power_flag("VBUS")   # from the USB host

    # --- power: VBAT -> 5.55 V buck -> diode OR with VBUS -> +5V -> 3.3 V LDO ---------------------
    with c.block("Buck VBAT -> 5.5V (LMR36506, 65 V)"):
        u2 = c.part("U2", "LMR36506RRPER")
        l1 = c.part("L1", "FNR3015S220MT")
        c_in = c.passive("C1", "C", "2.2uF", "0805", lcsc=C2U2_50V)
        c_hf = c.passive("C2", "C", "100nF", "0402", lcsc=C100N)
        c_bt = c.passive("C3", "C", "100nF", "0402", lcsc=C100N)
        c_vcc = c.passive("C4", "C", "1uF", "0402", lcsc=C1U)
        c_out = c.passive("C5", "C", "22uF", "0805", lcsc=C22U_25V)
        r_fbt = c.passive("R5", "R", "100k", "0402", lcsc=R100K)
        r_fbb = c.passive("R6", "R", "22k", "0402", lcsc=R22K)
        d1 = c.part("D1", "B5819W_SL")
    c.connect("VBAT", u2.VIN, u2.EN, c_in["1"], c_hf["1"])
    c.connect("GND", u2.GND, c_in["2"], c_hf["2"], c_vcc["2"], c_out["2"], r_fbb["2"])
    c.connect("BUCK_VCC", u2.VCC, u2.RT, c_vcc["1"])          # RT to VCC = 1 MHz (table 8-1)
    c.connect("BUCK_SW", u2.SW, l1["1"], c_bt["2"])
    c.connect("BUCK_BOOT", u2.BOOT, c_bt["1"])
    c.connect("V5_BUCK", l1["2"], c_out["1"], r_fbt["1"], d1.A)
    c.connect("BUCK_FB", u2.FB, r_fbt["2"], r_fbb["1"])
    c.nc(u2.PGOOD)
    c.power_flag("V5_BUCK")   # driven through L1, which ERC can't see

    with c.block("+5V rail and 3.3 V LDO"):
        u3 = c.part("U3", "XC6206P332MR-G")
        c_5v = c.passive("C6", "C", "4.7uF", "0402", lcsc=C4U7)
        c_ldo_in = c.passive("C7", "C", "1uF", "0402", lcsc=C1U)
        c_ldo_out = c.passive("C8", "C", "1uF", "0402", lcsc=C1U)
        c_3v3 = c.passive("C9", "C", "4.7uF", "0402", lcsc=C4U7)
    c.connect("+5V", d1.K, d2.K, c_5v["1"], u3.VIN, c_ldo_in["1"])
    c.connect("3V3", u3.VOUT, c_ldo_out["1"], c_3v3["1"])
    c.connect("GND", u3.VSS, c_5v["2"], c_ldo_in["2"], c_ldo_out["2"], c_3v3["2"])
    c.power_flag("+5V")   # ORed through D1/D2

    # --- MCU -------------------------------------------------------------------------------------
    with c.block("MCU STM32G431CBU6"):
        u1 = c.part("U1", "STM32G431CBU6")
        dec = [c.passive(f"C{10 + i}", "C", "100nF", "0402", lcsc=C100N) for i in range(3)]   # VDD 23/35/48
        c_bulk = c.passive("C13", "C", "4.7uF", "0402", lcsc=C4U7)
        c_vdda = c.passive("C14", "C", "1uF", "0402", lcsc=C1U)
        c_vdda_hf = c.passive("C15", "C", "100nF", "0402", lcsc=C100N)
        c_nrst = c.passive("C16", "C", "100nF", "0402", lcsc=C100N)
        r_boot = c.passive("R7", "R", "10k", "0402", lcsc=R10K)
        r_led = c.passive("R8", "R", "1k", "0402", lcsc=R1K)
        led = c.passive("D3", "LED", "red", "0603", lcsc="C2286")
    c.connect("3V3", u1.VDD, u1.VBAT, u1.VDDA, u1["VREF+"], *[d["1"] for d in dec], c_bulk["1"], c_vdda["1"], c_vdda_hf["1"])
    c.connect("GND", u1.VSS, *[d["2"] for d in dec], c_bulk["2"], c_vdda["2"], c_vdda_hf["2"], c_nrst["2"], r_boot["2"], led.K)
    c.connect("NRST", u1.PG10, c_nrst["1"])
    c.connect("BOOT0", u1.PB8, r_boot["1"])
    c.connect("LED", u1.PA4, r_led["1"])
    c.connect("LED_A", r_led["2"], led.A)
    c.connect("USB_DM", u1.PA11)
    c.connect("USB_DP", u1.PA12)
    c.connect("SWDIO", u1.PA13)
    c.connect("SWCLK", u1.PA14)
    c.connect("CRSF_RX", r_rx["2"], u1.PA10)    # USART1_RX
    c.connect("CRSF_TX", r_tx["2"], u1.PA9)     # USART1_TX
    c.nc(u1.PC13, u1.PC14, u1.PC15, u1.PF0, u1.PF1, u1.PA2, u1.PA5, u1.PA8, u1.PC4, u1.PB2, u1.PB10,
         u1.PB11, u1.PB12, u1.PB13, u1.PB14, u1.PB15, u1.PC6, u1.PC10, u1.PC11)

    # --- ESC interface: DShot out, current + battery voltage in, serial telemetry in -------------
    with c.block("ESC signals (DShot, current, telemetry, VBAT sense)"):
        r_m = [c.passive(f"R{9 + k}", "R", "100", "0402", lcsc=R100) for k in range(4)]
        r_cur_t = c.passive("R13", "R", "100k", "0402", lcsc=R100K)
        r_cur_b = c.passive("R14", "R", "10k", "0402", lcsc=R10K)
        c_cur = c.passive("C17", "C", "10nF", "0402", lcsc=C10N)
        r_vb_t = c.passive("R15", "R", "100k", "0402", lcsc=R100K)
        r_vb_b = c.passive("R16", "R", "10k", "0402", lcsc=R10K)
        c_vb = c.passive("C18", "C", "10nF", "0402", lcsc=C10N)
        r_tlm = c.passive("R17", "R", "1k", "0402", lcsc=R1K)
    for k, pin in enumerate((u1.PA6, u1.PA7, u1.PB0, u1.PB1)):   # TIM3_CH1..CH4
        c.connect(f"M{k + 1}", r_m[k]["1"])
        c.connect(f"DSHOT{k + 1}", r_m[k]["2"], pin)
    c.connect("ESC_CURR", r_cur_t["1"])
    c.connect("CURR_ADC", r_cur_t["2"], r_cur_b["1"], c_cur["1"], u1.PA1)   # ADC12_IN2
    c.connect("VBAT", r_vb_t["1"])
    c.connect("VBAT_ADC", r_vb_t["2"], r_vb_b["1"], c_vb["1"], u1.PA0)      # ADC12_IN1
    c.connect("GND", r_cur_b["2"], c_cur["2"], r_vb_b["2"], c_vb["2"])
    c.connect("ESC_TLM", r_tlm["1"])
    c.connect("TLM_RX", r_tlm["2"], u1.PA3)                                  # USART2_RX

    # --- IMU + log flash on SPI1 ----------------------------------------------------------------
    with c.block("IMU LSM6DSV32X + 16 MB log flash (SPI1)"):
        u4 = c.part("U4", "LSM6DSV32XTR")
        u5 = c.part("U5", "W25Q128JVPIQ")
        c_imu1 = c.passive("C19", "C", "100nF", "0402", lcsc=C100N)
        c_imu2 = c.passive("C20", "C", "100nF", "0402", lcsc=C100N)
        c_fl = c.passive("C21", "C", "100nF", "0402", lcsc=C100N)
        r_cs_imu = c.passive("R18", "R", "10k", "0402", lcsc=R10K)
        r_cs_fl = c.passive("R19", "R", "10k", "0402", lcsc=R10K)
    c.connect("SPI_SCK", u1.PB3, u4.SCL, u5.CLK)
    c.connect("SPI_MISO", u1.PB4, u4.SDO, u5.DO)
    c.connect("SPI_MOSI", u1.PB5, u4.SDA, u5.DI)
    c.connect("IMU_CS", u1.PA15, u4.CS, r_cs_imu["1"])
    c.connect("FLASH_CS", u1.PB6, u5.CS, r_cs_fl["1"])
    c.connect("IMU_INT1", u1.PB7, u4.INT1)
    c.nc(u1.PB9, u4.INT2)   # INT2 unused: one data-ready interrupt (INT1) is enough; frees a route at the MCU
    c.connect("3V3", u4.VDD, u4.VDDIO, u5.VCC, u5.WP, u5.HOLD, c_imu1["1"], c_imu2["1"], c_fl["1"],
              r_cs_imu["2"], r_cs_fl["2"])
    c.connect("GND", u4.GND, u4.SDX, u4.SCX, u5.GND, u5.EP, c_imu1["2"], c_imu2["2"], c_fl["2"])
    c.nc(u4.NC)

    # --- SWD / boot pads ------------------------------------------------------------------------
    with c.block("SWD + boot test pads"):
        tps = {n: c.part(f"TP{i + 1}", "TestPoint_1mm") for i, n in enumerate(("3V3", "GND", "SWDIO", "SWCLK", "NRST", "BOOT0"))}
    for n, tp in tps.items():
        c.connect(n, tp["1"])

    # --- net classes ----------------------------------------------------------------------------
    # 4-layer JLC rules, 0.5 mm QFN; 0.45/0.2 vias (JLC multilayer standard) so fan-out fits 3 signal layers
    c.net_class(NetClass("Default", track_width=0.15, clearance=0.125, via_diameter=0.45, via_drill=0.2))
    # same 0.45/0.2 vias: KiCad's SES import takes the drill from the net class and the pad from the
    # route, so mixed via sizes gave 0.45/0.3 vias (0.075 mm annular ring)
    c.net_class(NetClass("Power", track_width=0.4, clearance=0.15, current_a=0.5, via_diameter=0.45, via_drill=0.2),
                "VBAT", "GND", "+5V", "V5_BUCK", "VBUS", "3V3", "BUCK_SW")

    # --- design intent --------------------------------------------------------------------------
    vbat_max, vbat_spike = 26.1, 40.0
    v5 = 1.0 * (1 + 100e3 / 22e3)            # LMR36506 VREF 1.0 V
    vd = 0.35                                 # B5819W at ~0.25 A
    i3v3 = 0.080                              # MCU ~40 mA + flash write ~25 mA + IMU + LED
    c.check("Buck Vin: spike budget vs LMR36506 65 V", vbat_spike, 0, 65 * 0.9, "V")
    c.check("Buck output (RFBT 100k / RFBB 22k)", v5, 5.3, 5.8, "V")
    c.check("+5V rail after the OR diode (receiver supply)", v5 - vd, 4.75, 5.5, "V")
    c.check("+5V vs XC6206 6.0 V max input", v5, 0, 6.0, "V")
    c.check("XC6206 headroom (dropout ~0.25 V @ 100 mA)", v5 - vd - 3.3, 0.4, 3.0, "V")
    c.check("XC6206 dissipation (SOT-23 ~0.25 W)", (v5 - vd - 3.3) * i3v3, 0, 0.25, "W")
    c.check("+5V load: receiver 0.3 A + 3V3 rail vs LMR36506 0.6 A", 0.30 + i3v3, 0, 0.6, "A")
    l_ripple = (24 - v5) * v5 / (24 * 22e-6 * 1e6)
    c.check("Buck inductor peak (24 V in, 0.4 A load) vs Isat 0.68 A", 0.4 + l_ripple / 2, 0, 0.68 * 0.9, "A")
    c.check("VBAT_ADC at full LiHV (100k/10k)", vbat_max * 10 / 110, 0, 3.3, "V")
    c.check("CURR_ADC if the ESC cable is reversed (VBAT on CURR)", vbat_max * 10 / 110, 0, 3.3, "V")
    c.check("ESC current signal 3.3 V -> ADC counts after /11 (12-bit)", 3.3 / 11 / 3.3 * 4095, 300, 4095, "counts")
    c.check("Status LED current (Vf 1.8-2.4 V)", (3.3 - 1.9) / 1000, 0.5e-3, 5e-3, "A")
    return c

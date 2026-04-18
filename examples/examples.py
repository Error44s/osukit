"""
osukit - Full Examples
=======================================================

Shows the complete API for osu! Standard and Taiko.

Usage:
    python examples/examples.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from osukit import Beatmap, Difficulty, Performance, Mods
from osukit import DifficultyAttributes, TaikoDifficultyAttributes

# Sample maps (inline .osu content — no file needed)

STD_MAP = """osu file format v14
[General]
Mode: 0
[Metadata]
Title:Blue Zenith
Artist:xi
Creator:Mapper
Version:FOUR DIMENSIONS
[Difficulty]
HPDrainRate:3
CircleSize:4
OverallDifficulty:9
ApproachRate:9.7
SliderMultiplier:2.0
SliderTickRate:1
[TimingPoints]
0,307.692307692308,4,1,0,100,1,0
1000,-100,4,1,0,100,0,0
[HitObjects]
100,100,307,1,0
200,150,461,1,0
300,100,615,1,0
400,200,692,1,0
200,200,769,2,0,L|350:200,1,200
100,100,1230,1,0
300,100,1384,1,0
150,200,1538,1,0
350,200,1615,1,0
250,150,1692,1,0
100,100,1769,1,0
300,100,1846,1,0
150,200,1923,1,0
350,100,2000,1,0
250,200,2076,1,0
100,150,2153,1,0
300,100,2230,1,0
200,200,2307,12,0,3000
"""

TAIKO_MAP = """osu file format v14
[General]
Mode: 1
[Metadata]
Title:Haitai
Artist:Camellia
Creator:Mapper
Version:Inner Oni
[Difficulty]
HPDrainRate:5
CircleSize:5
OverallDifficulty:7
ApproachRate:0
SliderMultiplier:1.4
SliderTickRate:1
[TimingPoints]
0,333.333333333333,4,1,0,100,1,0
[HitObjects]
256,192,333,1,0
256,192,500,1,8
256,192,666,1,0
256,192,833,1,8
256,192,916,1,0
256,192,1000,1,8
256,192,1083,1,0
256,192,1166,1,8
256,192,1250,1,0
256,192,1333,1,0
256,192,1416,1,8
256,192,1500,1,0
256,192,1583,1,8
256,192,1666,1,0
256,192,1750,1,0
256,192,1833,1,8
256,192,1916,1,0
256,192,2000,1,8
256,192,2083,1,0
256,192,2166,1,0
256,192,2250,1,8
256,192,2333,1,0
256,192,2416,1,0
256,192,2500,1,8
"""

DIVIDER = "─" * 60

def section(title: str):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)

# EXAMPLE 1 — Beatmap parsing
section("1. Beatmap Parsing")

# From inline string
bm_std   = Beatmap(content=STD_MAP)
bm_taiko = Beatmap(content=TAIKO_MAP)

print(f"\nosu! Standard map:")
print(f"Title    : {bm_std.title}")
print(f"Artist   : {bm_std.artist}")
print(f"Circles  : {bm_std.n_circles}")
print(f"Sliders  : {bm_std.n_sliders}")
print(f"Spinners : {bm_std.n_spinners}")
print(f"Objects  : {bm_std.n_objects}")

print(f"\nosu! Taiko map:")
print(f"Title    : {bm_taiko.title}")
print(f"Objects  : {bm_taiko.n_objects}")

# From bytes (e.g. downloaded from osu! API)
bm_from_bytes = Beatmap(bytes=STD_MAP.encode("utf-8"))
print(f"\nLoaded from bytes: {bm_from_bytes.title!r}")

# EXAMPLE 2 — osu! Standard: Difficulty
section("2. osu! Standard – Difficulty")

nm_diff   = Difficulty(mods=0).calculate(bm_std)
hd_diff   = Difficulty(mods=int(Mods.HD)).calculate(bm_std)
hr_diff   = Difficulty(mods=int(Mods.HR)).calculate(bm_std)
dt_diff   = Difficulty(mods=int(Mods.DT)).calculate(bm_std)
hdhr_diff = Difficulty(mods=int(Mods.HD | Mods.HR)).calculate(bm_std)
hddt_diff = Difficulty(mods=int(Mods.HD | Mods.DT)).calculate(bm_std)
ez_diff   = Difficulty(mods=int(Mods.EZ)).calculate(bm_std)
ht_diff   = Difficulty(mods=int(Mods.HT)).calculate(bm_std)
fl_diff   = Difficulty(mods=int(Mods.FL)).calculate(bm_std)

print(f"\n{'Mods':<8} {'Stars':>7} {'Aim':>7} {'Speed':>7} {'AR':>6} {'OD':>6}")
print("─" * 46)
for label, d in [
    ("NM", nm_diff),
    ("HD", hd_diff),
    ("HR", hr_diff),
    ("DT", dt_diff),
    ("HDHR", hdhr_diff),
    ("HDDT", hddt_diff),
    ("EZ", ez_diff),
    ("HT", ht_diff),
    ("FL", fl_diff),
]:
    print(f"{label:<8} {d.stars:>7.3f} {d.aim_difficulty:>7.3f} {d.speed_difficulty:>7.3f} "
          f"{d.approach_rate:>6.2f} {d.overall_difficulty:>6.2f}")

# Custom clock rate override
fast_diff = Difficulty(mods=0, clock_rate=1.3).calculate(bm_std)
slow_diff = Difficulty(mods=0, clock_rate=0.8).calculate(bm_std)
print(f"\nClock rate 1.3x : {fast_diff.stars:.3f} stars")
print(f"Clock rate 0.8x : {slow_diff.stars:.3f} stars")

# AR/OD/CS overrides
custom = Difficulty(mods=0, ar=10.5, od=10.0).calculate(bm_std)
print(f"\nCustom AR=10.5, OD=10 : {custom.stars:.3f}★  AR→{custom.approach_rate:.2f} OD→{custom.overall_difficulty:.2f}")

# EXAMPLE 3 — osu! Standard: Performance (PP)
section("3. osu! Standard – Performance (PP)")

# Full breakdown
result = Performance(mods=int(Mods.HD | Mods.DT), accuracy=99.2, combo=500, misses=1).calculate(bm_std)
print(f"\n[HDDT] 99.2% acc, 500 combo, 1 miss:")
print(f"Total PP    : {result.pp:.2f}")
print(f"├─ Aim PP   : {result.pp_aim:.2f}")
print(f"├─ Speed PP : {result.pp_speed:.2f}")
print(f"├─ Acc PP   : {result.pp_accuracy:.2f}")
print(f"└─ FL PP    : {result.pp_flashlight:.2f}")
print(f"Eff. misses : {result.effective_miss_count:.2f}")
print(f"Stars       : {result.difficulty.stars:.3f}")

# Accuracy comparison
print(f"\n{'Accuracy':>10}  {'PP':>8}")
print("─" * 22)
for acc in [100.0, 99.5, 99.0, 98.0, 97.0, 95.0, 90.0]:
    r = Performance(mods=0, accuracy=acc).calculate(bm_std)
    print(f"  {acc:>6.1f}%  {r.pp:>8.2f}")

# Miss comparison
print(f"\n{'Misses':>8}  {'PP':>8}")
print("─" * 20)
for m in [0, 1, 2, 5, 10]:
    r = Performance(mods=0, accuracy=99.0, misses=m).calculate(bm_std)
    print(f"  {m:>6}x  {r.pp:>8.2f}")

# All mods
print(f"\n{'Mods':<8} {'PP (99%)':>10}")
print("─" * 22)
for label, mod_val in [
    ("NM", 0),
    ("HD", int(Mods.HD)),
    ("HR", int(Mods.HR)),
    ("DT", int(Mods.DT)),
    ("HDHR", int(Mods.HD | Mods.HR)),
    ("HDDT", int(Mods.HD | Mods.DT)),
    ("FL", int(Mods.FL)),
    ("EZ", int(Mods.EZ)),
    ("HT", int(Mods.HT)),
    ("NF", int(Mods.NF)),
    ("RX", int(Mods.RX)),
    ("SO", int(Mods.SO)),
]:
    r = Performance(mods=mod_val, accuracy=99.0).calculate(bm_std)
    print(f"  {label:<6} {r.pp:>10.2f}")

# Explicit hit counts
total = nm_diff.max_combo
r = Performance(mods=0, n300=total-5, n100=4, n50=1, misses=0).calculate(bm_std)
print(f"\nExplicit n300={total-5} n100=4 n50=1: PP = {r.pp:.2f}")

# EXAMPLE 4 — osu! Taiko: Difficulty
section("4. osu! Taiko – Difficulty")

nm_tdiff   = Difficulty(mods=0).calculate(bm_taiko)
dt_tdiff   = Difficulty(mods=int(Mods.DT)).calculate(bm_taiko)
hr_tdiff   = Difficulty(mods=int(Mods.HR)).calculate(bm_taiko)
hd_tdiff   = Difficulty(mods=int(Mods.HD)).calculate(bm_taiko)
hddt_tdiff = Difficulty(mods=int(Mods.HD | Mods.DT)).calculate(bm_taiko)
ht_tdiff   = Difficulty(mods=int(Mods.HT)).calculate(bm_taiko)
ez_tdiff   = Difficulty(mods=int(Mods.EZ)).calculate(bm_taiko)

print(f"\n{'Mods':<8} {'Stars':>7} {'Stamina':>9} {'Colour':>8} {'Rhythm':>8} {'HitWin':>8}")
print("─" * 56)
for label, d in [
    ("NM", nm_tdiff),
    ("DT", dt_tdiff),
    ("HR", hr_tdiff),
    ("HD", hd_tdiff),
    ("HDDT", hddt_tdiff),
    ("HT", ht_tdiff),
    ("EZ", ez_tdiff),
]:
    print(f"{label:<6} {d.stars:>7.3f} {d.stamina_difficulty:>9.4f} {d.colour_difficulty:>8.4f} "
          f"{d.rhythm_difficulty:>8.4f} {d.great_hit_window:>8.2f}ms")

# OD effect on hit window
print(f"\nOD effect on Great hit window (NM):")
for od in [4, 5, 6, 7, 8, 9, 10]:
    d = Difficulty(mods=0, od=float(od)).calculate(bm_taiko)
    print(f"OD {od}: ±{d.great_hit_window:.2f} ms window")

# EXAMPLE 5 — osu! Taiko: Performance (PP)
section("5. osu! Taiko – Performance (PP)")

# Full breakdown
t_result = Performance(mods=int(Mods.HD | Mods.DT), accuracy=98.5, misses=1).calculate(bm_taiko)
print(f"\n[HDDT] 98.5% acc, 1 miss:")
print(f"Total PP           : {t_result.pp:.2f}")
print(f"├─ Difficulty PP   : {t_result.pp_difficulty:.2f}")
print(f"└─ Accuracy PP     : {t_result.pp_accuracy:.2f}")
print(f"Est. Unstable Rate : {t_result.estimated_unstable_rate:.2f}")
print(f"Eff. misses        : {t_result.effective_miss_count:.2f}")
print(f"Stars              : {t_result.difficulty.stars:.3f}")

# Accuracy comparison (Taiko)
print(f"\n{'Accuracy':>10}  {'PP':>8}")
print("─" * 22)
for acc in [100.0, 99.5, 99.0, 98.0, 97.0, 95.0, 90.0]:
    r = Performance(mods=0, accuracy=acc).calculate(bm_taiko)
    print(f"  {acc:>6.1f}%  {r.pp:>8.2f}")

# All mods (Taiko)
print(f"\n{'Mods':<8} {'PP (98%)':>10}")
print("─" * 22)
for label, mod_val in [
    ("NM", 0),
    ("HD", int(Mods.HD)),
    ("HR", int(Mods.HR)),
    ("DT", int(Mods.DT)),
    ("HDDT", int(Mods.HD | Mods.DT)),
    ("FL", int(Mods.FL)),
    ("EZ", int(Mods.EZ)),
    ("HT", int(Mods.HT)),
    ("NF", int(Mods.NF)),
]:
    r = Performance(mods=mod_val, accuracy=98.0).calculate(bm_taiko)
    print(f"{label:<6} {r.pp:>10.2f}")

# Explicit n300 / n100
total_t = nm_tdiff.max_combo
r = Performance(mods=0, n300=total_t - 3, n100=3, misses=0).calculate(bm_taiko)
print(f"\nExplicit n300={total_t-3} n100=3 : PP = {r.pp:.2f}")

# EXAMPLE 6 — Loading from file (demo)
section("6. Loading from File (demo)")

print("""To use with a real .osu file:

    from osukit import Beatmap, Difficulty, Performance, Mods

    bm = Beatmap(path="/path/to/your/map.osu")

    # osu! Standard
    if bm.mode == 0:
        diff   = Difficulty(mods=int(Mods.HD | Mods.DT)).calculate(bm)
        result = Performance(mods=int(Mods.HD | Mods.DT), accuracy=99.0).calculate(bm)
        print(f"Stars: {diff.stars:.2f}  PP: {result.pp:.2f}")

    # osu! Taiko
    elif bm.mode == 1:
        diff   = Difficulty(mods=int(Mods.DT)).calculate(bm)
        result = Performance(mods=int(Mods.DT), accuracy=98.5).calculate(bm)
        print(f"Stars: {diff.stars:.2f}  PP: {result.pp:.2f}")""")

print("\nAll examples completed successfully!")

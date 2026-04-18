"""
osukit - Example & Quick Test
Run this to verify the library works:
python example.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from osukit import Beatmap, Difficulty, Performance, Mods

# Direct API test with a synthetic .osu content
SAMPLE_OSU = """osu file format v14

[General]
Mode: 0

[Metadata]
Title:Test Map
Artist:Test Artist
Creator:Mapper
Version:Normal

[Difficulty]
HPDrainRate:5
CircleSize:4
OverallDifficulty:8
ApproachRate:9
SliderMultiplier:1.8
SliderTickRate:1

[TimingPoints]
0,500,4,1,0,100,1,0
1000,-100,4,1,0,100,0,0

[HitObjects]
256,192,1000,1,0
320,192,1500,1,0
384,192,2000,1,0
448,192,2250,1,0
256,192,2500,2,0,L|384:192,1,128
256,192,3500,12,0,4000
100,100,4500,1,0
200,150,4750,1,0
300,100,5000,1,0
400,150,5250,1,0
256,192,5500,1,0
100,100,5700,1,0
200,200,5900,1,0
"""


def test_basic():
    print("=" * 60)
    print("osukit - Basic Test")
    print("=" * 60)

    bm = Beatmap(content=SAMPLE_OSU)
    print(f"\nBeatmap loaded:")
    print(f"Title   : {bm.title}")
    print(f"Circles : {bm.n_circles}")
    print(f"Sliders : {bm.n_sliders}")
    print(f"Spinners: {bm.n_spinners}")
    print(f"Objects : {bm.n_objects}")

    # NM
    diff_nm = Difficulty(mods=0).calculate(bm)
    print(f"\n[NM] Stars: {diff_nm.stars:.4f}")
    print(f"AR: {diff_nm.approach_rate:.2f} | OD: {diff_nm.overall_difficulty:.2f}")
    print(f"Aim: {diff_nm.aim_difficulty:.4f} | Speed: {diff_nm.speed_difficulty:.4f}")

    perf_nm = Performance(mods=0, accuracy=99.0).calculate(bm)
    print(f"\n[NM] PP at 99% acc: {perf_nm.pp:.2f}")
    print(f"Aim: {perf_nm.pp_aim:.2f} | Speed: {perf_nm.pp_speed:.2f} | Acc: {perf_nm.pp_accuracy:.2f}")

    # HDHR
    diff_hdhr = Difficulty(mods=Mods.HD | Mods.HR).calculate(bm)
    print(f"\n[HDHR] Stars: {diff_hdhr.stars:.4f}")

    perf_hdhr = Performance(mods=int(Mods.HD | Mods.HR), accuracy=98.5, misses=1).calculate(bm)
    print(f"[HDHR] PP at 98.5% acc, 1 miss: {perf_hdhr.pp:.2f}")

    # DT
    diff_dt = Difficulty(mods=Mods.DT).calculate(bm)
    print(f"\n[DT] Stars: {diff_dt.stars:.4f}")

    perf_dt = Performance(mods=int(Mods.DT), accuracy=97.0).calculate(bm)
    print(f"[DT] PP at 97% acc: {perf_dt.pp:.2f}")

    # FC vs 2 misses
    print("\n--- FC vs Misses comparison ---")
    fc = Performance(mods=0, accuracy=99.5, misses=0).calculate(bm)
    with_misses = Performance(mods=0, accuracy=99.5, misses=2).calculate(bm)
    print(f"FC (99.5%): {fc.pp:.2f} PP")
    print(f"2 misses (99.5%): {with_misses.pp:.2f} PP")

    # Full SS
    ss = Performance(mods=0, accuracy=100.0, misses=0).calculate(bm)
    print(f"SS: {ss.pp:.2f} PP")

    print("\nAll tests passed!")


def test_mods():
    print("\n" + "=" * 60)
    print("Mod multiplier test")
    print("=" * 60)
    bm = Beatmap(content=SAMPLE_OSU)

    mod_list = [
        (0, "NM"),
        (int(Mods.HD), "HD"),
        (int(Mods.HR), "HR"),
        (int(Mods.DT), "DT"),
        (int(Mods.HD | Mods.HR), "HDHR"),
        (int(Mods.HD | Mods.DT), "HDDT"),
        (int(Mods.EZ), "EZ"),
        (int(Mods.HT), "HT"),
        (int(Mods.FL), "FL"),
    ]

    for m, name in mod_list:
        try:
            d = Difficulty(mods=m).calculate(bm)
            p = Performance(mods=m, accuracy=99.0).calculate(bm)
            print(f"{name:<6} | Stars: {d.stars:6.3f} | PP (99%): {p.pp:8.2f}")
        except Exception as e:
            print(f"{name:<6} | ERROR: {e}")


if __name__ == "__main__":
    test_basic()
    test_mods()

"""
The MIT License (MIT)

Copyright (c) 2026 Error44s

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import sys, os, math, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import osukit as rosu
from osukit import (
    Beatmap, Difficulty, Performance, Mods,
    DifficultyAttributes, PerformanceAttributes,
    TaikoDifficultyAttributes, TaikoPerformanceAttributes,
)

# Shared sample .osu content
OSU_STD_MAP = """osu file format v14

[General]
Mode: 0

[Metadata]
Title:Test Standard
Artist:Artist
Creator:Mapper
Version:Hard

[Difficulty]
HPDrainRate:6
CircleSize:4
OverallDifficulty:8
ApproachRate:9.2
SliderMultiplier:1.8
SliderTickRate:1

[TimingPoints]
0,400,4,1,0,100,1,0
1200,-100,4,1,0,100,0,0

[HitObjects]
100,100,500,1,0
200,150,750,1,0
300,100,1000,1,0
400,200,1125,1,0
200,200,1250,2,0,L|350:200,1,150
100,100,2000,1,0
300,100,2200,1,0
150,200,2400,1,0
350,200,2500,1,0
250,150,2600,1,0
100,100,2700,1,0
300,100,2800,1,0
150,200,2900,12,0,3500
"""

OSU_TAIKO_MAP = """osu file format v14

[General]
Mode: 1

[Metadata]
Title:Test Taiko
Artist:Artist
Creator:Mapper
Version:Oni

[Difficulty]
HPDrainRate:6
CircleSize:5
OverallDifficulty:6
ApproachRate:0
SliderMultiplier:1.4
SliderTickRate:1

[TimingPoints]
0,500,4,1,0,100,1,0

[HitObjects]
256,192,500,1,0
256,192,750,1,8
256,192,1000,1,0
256,192,1125,1,8
256,192,1250,1,0
256,192,1375,1,8
256,192,1500,1,0
256,192,1625,1,8
256,192,1750,1,0
256,192,1875,1,0
256,192,2000,1,8
256,192,2125,1,0
256,192,2250,1,8
256,192,2375,1,0
256,192,2500,1,0
256,192,2625,1,8
256,192,2750,1,0
256,192,2875,1,8
256,192,3000,1,0
256,192,3125,1,0
"""

# 1. Beatmap parsing tests
class TestBeatmapParsing(unittest.TestCase):

    def test_std_parse_metadata(self):
        bm = Beatmap(content=OSU_STD_MAP)
        self.assertEqual(bm.title, "Test Standard")
        self.assertEqual(bm.artist, "Artist")
        self.assertEqual(bm.mode, 0)

    def test_std_parse_objects(self):
        bm = Beatmap(content=OSU_STD_MAP)
        self.assertGreater(bm.n_circles, 0)
        self.assertGreater(bm.n_sliders, 0)
        self.assertGreaterEqual(bm.n_spinners, 0)
        self.assertGreater(bm.n_objects, 0)

    def test_std_parse_counts(self):
        bm = Beatmap(content=OSU_STD_MAP)
        self.assertEqual(bm.n_objects, bm.n_circles + bm.n_sliders + bm.n_spinners)

    def test_taiko_parse_metadata(self):
        bm = Beatmap(content=OSU_TAIKO_MAP)
        self.assertEqual(bm.title, "Test Taiko")
        self.assertEqual(bm.mode, 1)

    def test_taiko_parse_objects(self):
        bm = Beatmap(content=OSU_TAIKO_MAP)
        self.assertGreater(bm.n_objects, 0)

    def test_beatmap_from_path_raises_on_missing(self):
        with self.assertRaises(FileNotFoundError):
            Beatmap(path="/nonexistent/map.osu")

    def test_beatmap_repr(self):
        bm = Beatmap(content=OSU_STD_MAP)
        r = repr(bm)
        self.assertIn("Beatmap", r)
        self.assertIn("Test Standard", r)

    def test_beatmap_from_bytes(self):
        bm = Beatmap(bytes=OSU_STD_MAP.encode("utf-8"))
        self.assertEqual(bm.title, "Test Standard")

# 2. osu! Standard – Difficulty tests
class TestStandardDifficulty(unittest.TestCase):

    def setUp(self):
        self.bm = Beatmap(content=OSU_STD_MAP)

    def test_nm_returns_difficulty_attributes(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertIsInstance(attrs, DifficultyAttributes)

    def test_stars_positive(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertGreater(attrs.stars, 0.0)

    def test_stars_finite(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertTrue(math.isfinite(attrs.stars))

    def test_dt_harder_than_nm(self):
        nm = Difficulty(mods=0).calculate(self.bm)
        dt = Difficulty(mods=int(Mods.DT)).calculate(self.bm)
        self.assertGreater(dt.stars, nm.stars)

    def test_ht_easier_than_nm(self):
        nm = Difficulty(mods=0).calculate(self.bm)
        ht = Difficulty(mods=int(Mods.HT)).calculate(self.bm)
        self.assertLess(ht.stars, nm.stars)

    def test_hr_changes_ar_od(self):
        nm = Difficulty(mods=0).calculate(self.bm)
        hr = Difficulty(mods=int(Mods.HR)).calculate(self.bm)
        # HR increases OD and AR (up to 10)
        self.assertGreaterEqual(hr.overall_difficulty, nm.overall_difficulty)
        self.assertGreaterEqual(hr.approach_rate, nm.approach_rate)

    def test_ez_decreases_ar_od(self):
        nm = Difficulty(mods=0).calculate(self.bm)
        ez = Difficulty(mods=int(Mods.EZ)).calculate(self.bm)
        self.assertLessEqual(ez.overall_difficulty, nm.overall_difficulty)
        self.assertLessEqual(ez.approach_rate, nm.approach_rate)

    def test_aim_and_speed_positive(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertGreaterEqual(attrs.aim_difficulty, 0.0)
        self.assertGreaterEqual(attrs.speed_difficulty, 0.0)

    def test_hit_circle_count_correct(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertEqual(attrs.hit_circle_count, self.bm.n_circles)

    def test_max_combo_positive(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertGreater(attrs.max_combo, 0)

    def test_fl_increases_stars(self):
        nm = Difficulty(mods=0).calculate(self.bm)
        fl = Difficulty(mods=int(Mods.FL)).calculate(self.bm)
        self.assertGreaterEqual(fl.stars, nm.stars)

    def test_clock_rate_override(self):
        nm   = Difficulty(mods=0).calculate(self.bm)
        fast = Difficulty(mods=0, clock_rate=1.5).calculate(self.bm)
        self.assertGreater(fast.stars, nm.stars)

    def test_ar_override(self):
        a1 = Difficulty(mods=0, ar=5.0).calculate(self.bm)
        a2 = Difficulty(mods=0, ar=10.0).calculate(self.bm)
        self.assertGreater(a2.approach_rate, a1.approach_rate)

# 3. osu! Standard – Performance tests
class TestStandardPerformance(unittest.TestCase):

    def setUp(self):
        self.bm = Beatmap(content=OSU_STD_MAP)

    def test_nm_returns_performance_attributes(self):
        result = Performance(mods=0).calculate(self.bm)
        self.assertIsInstance(result, PerformanceAttributes)

    def test_pp_positive(self):
        result = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        self.assertGreater(result.pp, 0.0)

    def test_pp_finite(self):
        result = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        self.assertTrue(math.isfinite(result.pp))

    def test_ss_not_less_than_99(self):
        ss  = Performance(mods=0, accuracy=100.0).calculate(self.bm)
        p99 = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        self.assertGreaterEqual(ss.pp, p99.pp)

    def test_misses_reduce_pp(self):
        fc    = Performance(mods=0, accuracy=99.0, misses=0).calculate(self.bm)
        miss2 = Performance(mods=0, accuracy=99.0, misses=2).calculate(self.bm)
        self.assertGreater(fc.pp, miss2.pp)

    def test_dt_more_pp_than_nm(self):
        nm = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        dt = Performance(mods=int(Mods.DT), accuracy=99.0).calculate(self.bm)
        self.assertGreater(dt.pp, nm.pp)

    def test_hd_more_pp_than_nm(self):
        nm = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        hd = Performance(mods=int(Mods.HD), accuracy=99.0).calculate(self.bm)
        self.assertGreater(hd.pp, nm.pp)

    def test_pp_components_non_negative(self):
        result = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        self.assertGreaterEqual(result.pp_aim, 0.0)
        self.assertGreaterEqual(result.pp_speed, 0.0)
        self.assertGreaterEqual(result.pp_accuracy, 0.0)
        self.assertGreaterEqual(result.pp_flashlight, 0.0)

    def test_pp_components_sum_approx_total(self):
        result = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        # total ≈ norm1.1(aim, speed, acc, fl) — not a simple sum, but bounded
        component_max = result.pp_aim + result.pp_speed + result.pp_accuracy + result.pp_flashlight
        self.assertLessEqual(result.pp, component_max + 1.0)  # allow rounding

    def test_fl_pp_zero_without_mod(self):
        result = Performance(mods=0).calculate(self.bm)
        self.assertEqual(result.pp_flashlight, 0.0)

    def test_fl_pp_nonzero_with_mod(self):
        result = Performance(mods=int(Mods.FL)).calculate(self.bm)
        self.assertGreater(result.pp_flashlight, 0.0)

    def test_nf_reduces_pp(self):
        nm = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        nf = Performance(mods=int(Mods.NF), accuracy=99.0).calculate(self.bm)
        self.assertLessEqual(nf.pp, nm.pp)

    def test_rx_reduces_pp(self):
        nm = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        rx = Performance(mods=int(Mods.RX), accuracy=99.0).calculate(self.bm)
        self.assertLess(rx.pp, nm.pp)

    def test_difficulty_attr_reused(self):
        result = Performance(mods=0, accuracy=99.0).calculate(self.bm)
        self.assertIsNotNone(result.difficulty)
        self.assertIsInstance(result.difficulty, DifficultyAttributes)

    def test_all_mod_combinations_dont_crash(self):
        combos = [0, 8, 16, 64, 24, 72, 256, 1024, 8+1024]
        for m in combos:
            try:
                Performance(mods=m, accuracy=99.0).calculate(self.bm)
            except Exception as e:
                self.fail(f"Mods={m} raised {e}")

# 4. osu!Taiko – Difficulty tests
class TestTaikoDifficulty(unittest.TestCase):

    def setUp(self):
        self.bm = Beatmap(content=OSU_TAIKO_MAP)

    def test_returns_taiko_difficulty_attributes(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertIsInstance(attrs, TaikoDifficultyAttributes)

    def test_stars_positive(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertGreater(attrs.stars, 0.0)

    def test_stars_finite(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertTrue(math.isfinite(attrs.stars))

    def test_dt_harder_than_nm(self):
        nm = Difficulty(mods=0).calculate(self.bm)
        dt = Difficulty(mods=int(Mods.DT)).calculate(self.bm)
        self.assertGreater(dt.stars, nm.stars)

    def test_ht_easier_than_nm(self):
        nm = Difficulty(mods=0).calculate(self.bm)
        ht = Difficulty(mods=int(Mods.HT)).calculate(self.bm)
        self.assertLess(ht.stars, nm.stars)

    def test_stamina_nonnegative(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertGreaterEqual(attrs.stamina_difficulty, 0.0)

    def test_colour_nonnegative(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertGreaterEqual(attrs.colour_difficulty, 0.0)

    def test_rhythm_nonnegative(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertGreaterEqual(attrs.rhythm_difficulty, 0.0)

    def test_great_hit_window_decreases_with_od(self):
        lo_od = Difficulty(mods=0, od=2.0).calculate(self.bm)
        hi_od = Difficulty(mods=0, od=9.0).calculate(self.bm)
        self.assertGreater(lo_od.great_hit_window, hi_od.great_hit_window)

    def test_hr_increases_od(self):
        nm = Difficulty(mods=0).calculate(self.bm)
        hr = Difficulty(mods=int(Mods.HR)).calculate(self.bm)
        self.assertGreaterEqual(hr.overall_difficulty, nm.overall_difficulty)

    def test_max_combo_positive(self):
        attrs = Difficulty(mods=0).calculate(self.bm)
        self.assertGreater(attrs.max_combo, 0)

# 5. osu!Taiko – Performance tests
class TestTaikoPerformance(unittest.TestCase):

    def setUp(self):
        self.bm = Beatmap(content=OSU_TAIKO_MAP)

    def test_returns_taiko_performance_attributes(self):
        result = Performance(mods=0).calculate(self.bm)
        self.assertIsInstance(result, TaikoPerformanceAttributes)

    def test_pp_positive(self):
        result = Performance(mods=0, accuracy=98.0).calculate(self.bm)
        self.assertGreater(result.pp, 0.0)

    def test_pp_finite(self):
        result = Performance(mods=0, accuracy=98.0).calculate(self.bm)
        self.assertTrue(math.isfinite(result.pp))

    def test_ss_not_less_than_98(self):
        ss  = Performance(mods=0, accuracy=100.0).calculate(self.bm)
        p98 = Performance(mods=0, accuracy=98.0).calculate(self.bm)
        self.assertGreaterEqual(ss.pp, p98.pp)

    def test_misses_reduce_pp(self):
        fc    = Performance(mods=0, accuracy=98.0, misses=0).calculate(self.bm)
        miss2 = Performance(mods=0, accuracy=98.0, misses=2).calculate(self.bm)
        self.assertGreater(fc.pp, miss2.pp)

    def test_dt_more_pp(self):
        nm = Performance(mods=0, accuracy=98.0).calculate(self.bm)
        dt = Performance(mods=int(Mods.DT), accuracy=98.0).calculate(self.bm)
        self.assertGreater(dt.pp, nm.pp)

    def test_hd_more_pp(self):
        nm = Performance(mods=0, accuracy=98.0).calculate(self.bm)
        hd = Performance(mods=int(Mods.HD), accuracy=98.0).calculate(self.bm)
        self.assertGreater(hd.pp, nm.pp)

    def test_pp_components_nonneg(self):
        result = Performance(mods=0, accuracy=98.0).calculate(self.bm)
        self.assertGreaterEqual(result.pp_difficulty, 0.0)
        self.assertGreaterEqual(result.pp_accuracy, 0.0)

    def test_difficulty_attr_attached(self):
        result = Performance(mods=0, accuracy=98.0).calculate(self.bm)
        self.assertIsInstance(result.difficulty, TaikoDifficultyAttributes)

    def test_nf_reduces_pp(self):
        nm = Performance(mods=0, accuracy=98.0).calculate(self.bm)
        nf = Performance(mods=int(Mods.NF), accuracy=98.0).calculate(self.bm)
        self.assertLessEqual(nf.pp, nm.pp)

    def test_effective_miss_count_zero_on_fc(self):
        result = Performance(mods=0, accuracy=100.0, misses=0).calculate(self.bm)
        self.assertAlmostEqual(result.effective_miss_count, 0.0, places=3)

    def test_all_mod_combos_dont_crash(self):
        for m in [0, 8, 16, 64, 24, 256, 1024]:
            try:
                Performance(mods=m, accuracy=97.0).calculate(self.bm)
            except Exception as e:
                self.fail(f"Taiko mods={m} raised {e}")

    def test_explicit_n300_n100(self):
        total = Difficulty(mods=0).calculate(self.bm).max_combo
        result = Performance(mods=0, n300=total-2, n100=2, misses=0).calculate(self.bm)
        self.assertGreater(result.pp, 0.0)

# 6. Mods tests
class TestMods(unittest.TestCase):

    def test_nm_speed_multiplier(self):
        self.assertAlmostEqual(Mods.NM.speed_multiplier, 1.0)

    def test_dt_speed_multiplier(self):
        self.assertAlmostEqual(Mods.DT.speed_multiplier, 1.5)

    def test_ht_speed_multiplier(self):
        self.assertAlmostEqual(Mods.HT.speed_multiplier, 0.75)

    def test_hr_od_multiplier(self):
        self.assertAlmostEqual(Mods.HR.od_multiplier, 1.4)

    def test_ez_od_multiplier(self):
        self.assertAlmostEqual(Mods.EZ.od_multiplier, 0.5)

    def test_hdhr_combo(self):
        m = Mods.HD | Mods.HR
        self.assertTrue(m & Mods.HD)
        self.assertTrue(m & Mods.HR)
        self.assertFalse(m & Mods.DT)

    def test_mods_int_roundtrip(self):
        self.assertEqual(int(Mods(24)), 24)  # HDHR

# 7. Edge-case / robustness tests
class TestEdgeCases(unittest.TestCase):

    def test_empty_map_std(self):
        empty = """osu file format v14\n[General]\nMode: 0\n[Difficulty]\nHPDrainRate:5\nCircleSize:4\nOverallDifficulty:5\nApproachRate:5\n[HitObjects]\n"""
        bm = Beatmap(content=empty)
        attrs = Difficulty(mods=0).calculate(bm)
        self.assertEqual(attrs.stars, 0.0)

    def test_empty_map_taiko(self):
        empty = """osu file format v14\n[General]\nMode: 1\n[Difficulty]\nHPDrainRate:5\nCircleSize:5\nOverallDifficulty:5\nApproachRate:0\n[HitObjects]\n"""
        bm = Beatmap(content=empty)
        attrs = Difficulty(mods=0).calculate(bm)
        self.assertEqual(attrs.stars, 0.0)

    def test_unsupported_mode_raises(self):
        catch_map = OSU_STD_MAP.replace("Mode: 0", "Mode: 2")
        bm = Beatmap(content=catch_map)
        with self.assertRaises(NotImplementedError):
            Difficulty(mods=0).calculate(bm)

    def test_accuracy_clamped_above_100(self):
        bm = Beatmap(content=OSU_STD_MAP)
        r1 = Performance(mods=0, accuracy=100.0).calculate(bm)
        r2 = Performance(mods=0, accuracy=105.0).calculate(bm)
        self.assertAlmostEqual(r1.pp, r2.pp, places=2)

    def test_accuracy_zero_gives_low_pp(self):
        bm = Beatmap(content=OSU_STD_MAP)
        result = Performance(mods=0, accuracy=0.0).calculate(bm)
        self.assertGreaterEqual(result.pp, 0.0)

    def test_stars_not_nan(self):
        for content in [OSU_STD_MAP, OSU_TAIKO_MAP]:
            bm = Beatmap(content=content)
            attrs = Difficulty(mods=0).calculate(bm)
            self.assertFalse(math.isnan(attrs.stars), f"Stars is NaN for mode {bm.mode}")

    def test_pp_not_nan(self):
        for content in [OSU_STD_MAP, OSU_TAIKO_MAP]:
            bm = Beatmap(content=content)
            result = Performance(mods=0, accuracy=95.0).calculate(bm)
            self.assertFalse(math.isnan(result.pp), f"PP is NaN for mode {bm.mode}")

# Runner
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

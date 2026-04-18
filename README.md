# OsuKit

A **bot-first osu! toolkit for Python** with replay analysis, performance calculation, and advanced score insights.

---

### 🚀 Features

- Full local PP & difficulty calculation
- Replay parsing and per-object judgement reconstruction
- Fail / choke / partial run analysis
- Bot-first APIs for current/recent/profile/map/compare
- Skill insights and coaching-style recommendations
- Benchmarking & calibration system for PP accuracy

---

### 📊 Mode Coverage

| Mode          | Local Difficulty | Local PP | Replay Reconstruction | Partial/Fail Projection |
|---------------|:-:|:-:|:-:|:-:|
| osu!standard  | ✅ Full | ✅ Full | ✅ Full (circles, sliders, spinners) | ✅ |
| osu!taiko     | ✅ Full | ✅ Full | 🔶 Preview | ✅ |
| osu!catch     | ✅ Full | ✅ Full | 🔶 Preview | ✅ |
| osu!mania     | ✅ Full | ✅ Full | 🔶 Preview | ✅ |

---

### 📦 Installation

```bash
pip install osukit
pip install aiohttp  # optional
```

---

### ⚡ Quickstart

```python
from osukit import OsuBotClient

client = OsuBotClient.from_client_credentials(
    client_id=YOUR_CLIENT_ID,
    client_secret="YOUR_SECRET",
)

result = client.get_current_play("cookiezi")
print(result.summary)
```

---

### 🤖 Discord Bot Example

```python
@bot.command()
async def recent(ctx, username: str):
    result = await osu.aget_current_play(username)
    s = result.summary

    await ctx.send(
        f"**{s['player']}** — {s['title']}\n"
        f"{s['accuracy']:.2f}% | {s['current_pp']:.0f}pp"
    )
```

---

### 🎬 Replay Analysis

```python
from osukit import parse_osr_file, reconstruct_judgements, BeatmapResolver

replay = parse_osr_file("replay.osr")
beatmap = BeatmapResolver().resolve(beatmap_id=12345)

recon = reconstruct_judgements(beatmap, replay.frames, mods=replay.mods)

print(recon.statistics.count_300)
print(recon.statistics.count_miss)
```

---

### 📉 Fail Analysis

```python
from osukit import analyze_api_score

analysis = analyze_api_score(beatmap, api_score)

print(analysis.current_pp)
print(analysis.if_fc_pp)
print(analysis.choke_pp)
```

---

### 🧠 Insights

```python
from osukit import build_session_insight

session = build_session_insight(analyses)

print(session.profile.summary)
```

---

### 📊 Benchmarking

```python
from osukit import create_golden_case, run_golden_suite

case = create_golden_case(
    name="sample",
    beatmap_path="map.osu",
    accuracy=99.2,
)

report = run_golden_suite([case])
print(report.to_markdown())
```

---

### ⚠️ Disclaimer

This project is **not affiliated with or endorsed by osu! or ppy Pty Ltd.**

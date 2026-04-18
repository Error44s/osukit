"""Example discord.py slash command for the latest recent play.

Requirements:
    pip install discord.py

This example assumes you already have a bot token and an osu! API v2 bearer
access token. It also assumes you can resolve a local .osu file path for the
beatmap the user just played.
"""

from __future__ import annotations

import os
import discord
from discord.ext import commands

from osukit import Beatmap, OsuApiClient
from osukit.discord_ext import create_recent_command


DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', '')
OSU_BEARER_TOKEN = os.getenv('OSU_BEARER_TOKEN', '')

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
osu_client = OsuApiClient(token=OSU_BEARER_TOKEN)


def get_api_client(_interaction: discord.Interaction) -> OsuApiClient:
    return osu_client


def get_beatmap(_interaction: discord.Interaction, api_score: dict) -> Beatmap:
    # Replace this with your own cache/downloader/resolver.
    beatmap_id = api_score.get('beatmap', {}).get('id') or api_score.get('beatmap_id')
    local_path = f'beatmaps/{beatmap_id}.osu'
    return Beatmap(path=local_path)


bot.tree.add_command(create_recent_command(
    get_api_client=get_api_client,
    get_beatmap=get_beatmap,
    name='current',
    description='Show the latest recent osu! score',
))


@bot.event
async def on_ready() -> None:
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')


if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)

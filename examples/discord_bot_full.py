from discord.ext import commands
from osukit import BeatmapResolver, OsuBotClient
from osukit.discord_ext import (
    create_compare_command,
    create_current_command,
    create_fails_command,
    create_map_command,
    create_profile_command,
    create_top_command,
)

bot = commands.Bot(command_prefix='!')
resolver = BeatmapResolver(cache_dir='./beatmaps')
osu = OsuBotClient.from_client_credentials(
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    resolver=resolver,
)


def get_osu(_interaction):
    return osu


bot.tree.add_command(create_current_command(get_bot_client=get_osu))
bot.tree.add_command(create_profile_command(get_bot_client=get_osu))
bot.tree.add_command(create_top_command(get_bot_client=get_osu))
bot.tree.add_command(create_fails_command(get_bot_client=get_osu))
bot.tree.add_command(create_map_command(get_bot_client=get_osu))
bot.tree.add_command(create_compare_command(get_bot_client=get_osu))

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

from __future__ import annotations

from typing import Any, Callable, Optional

try: # pragma: no cover - optional dependency
    import discord
    from discord import app_commands
except Exception: # pragma: no cover - optional dependency
    discord = None
    app_commands = None


def _require_discord():
    if discord is None or app_commands is None: # pragma: no cover - optional dependency
        raise ImportError('discord.py is not installed. Install discord.py to use the discord extension helpers.')


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, '__await__'):
        return await value
    return value


def _embed_from_payload(payload: dict[str, Any]):
    embed = discord.Embed(title=payload['title'], description=payload.get('description'), color=payload.get('color'), url=payload.get('url'))
    for field in payload.get('fields', []):
        embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))
    footer = payload.get('footer') or {}
    if footer.get('text'):
        embed.set_footer(text=footer['text'])
    thumb = payload.get('thumbnail') or {}
    if thumb.get('url'):
        embed.set_thumbnail(url=thumb['url'])
    return embed


def create_current_command(*, get_bot_client: Callable[[Any], Any], name: str = 'current', description: str = 'Show the latest recent osu! play', include_fails: bool = True, mode: str = 'osu', default_color: Optional[int] = None):
    _require_discord()

    @app_commands.command(name=name, description=description)
    async def current(interaction: 'discord.Interaction', user: str):
        await interaction.response.defer(thinking=True)
        bot_client = get_bot_client(interaction)
        result = await _maybe_await(bot_client.aget_current_play(user, mode=mode, include_fails=include_fails))
        await interaction.followup.send(embed=_embed_from_payload(result.to_embed_payload(color=default_color)))

    return current


def create_profile_command(*, get_bot_client: Callable[[Any], Any], name: str = 'osu_profile', description: str = 'Show an osu! user profile', mode: str = 'osu', default_color: Optional[int] = None):
    _require_discord()

    @app_commands.command(name=name, description=description)
    async def profile(interaction: 'discord.Interaction', user: str):
        await interaction.response.defer(thinking=True)
        bot_client = get_bot_client(interaction)
        result = await _maybe_await(bot_client.aget_profile(user, mode=mode))
        await interaction.followup.send(embed=_embed_from_payload(result.to_embed_payload(color=default_color)))

    return profile


def create_top_command(*, get_bot_client: Callable[[Any], Any], name: str = 'osu_top', description: str = 'Show top osu! plays', mode: str = 'osu', default_color: Optional[int] = None, limit: int = 5):
    _require_discord()

    @app_commands.command(name=name, description=description)
    async def top(interaction: 'discord.Interaction', user: str):
        await interaction.response.defer(thinking=True)
        bot_client = get_bot_client(interaction)
        result = await _maybe_await(bot_client.aget_top_plays(user, mode=mode, limit=limit))
        await interaction.followup.send(embed=_embed_from_payload(result.to_embed_payload(color=default_color)))

    return top


def create_fails_command(*, get_bot_client: Callable[[Any], Any], name: str = 'osu_fails', description: str = 'Show recent failed plays', mode: str = 'osu', default_color: Optional[int] = None, limit: int = 5):
    _require_discord()

    @app_commands.command(name=name, description=description)
    async def fails(interaction: 'discord.Interaction', user: str):
        await interaction.response.defer(thinking=True)
        bot_client = get_bot_client(interaction)
        result = await _maybe_await(bot_client.aget_recent_fails(user, mode=mode, limit=limit))
        await interaction.followup.send(embed=_embed_from_payload(result.to_embed_payload(color=default_color)))

    return fails


def create_map_command(*, get_bot_client: Callable[[Any], Any], name: str = 'osu_map', description: str = 'Show a beatmap overview', default_color: Optional[int] = None):
    _require_discord()

    @app_commands.command(name=name, description=description)
    async def beatmap(interaction: 'discord.Interaction', beatmap_id: int):
        await interaction.response.defer(thinking=True)
        bot_client = get_bot_client(interaction)
        result = await _maybe_await(bot_client.aget_map(beatmap_id))
        await interaction.followup.send(embed=_embed_from_payload(result.to_embed_payload(color=default_color)))

    return beatmap


def create_compare_command(*, get_bot_client: Callable[[Any], Any], name: str = 'osu_compare', description: str = 'Compare two users on a beatmap', mode: str = 'osu', default_color: Optional[int] = None, include_fails: bool = True):
    _require_discord()

    @app_commands.command(name=name, description=description)
    async def compare(interaction: 'discord.Interaction', left_user: str, right_user: str, beatmap_id: int):
        await interaction.response.defer(thinking=True)
        bot_client = get_bot_client(interaction)
        result = await _maybe_await(bot_client.acompare_on_beatmap(left_user, right_user, beatmap_id=beatmap_id, mode=mode, include_fails=include_fails))
        await interaction.followup.send(embed=_embed_from_payload(result.to_embed_payload(color=default_color)))

    return compare


def create_recent_command(*, get_bot_client: Callable[[Any], Any], name: str = 'recent', description: str = 'Show recent osu! plays', include_fails: bool = True, mode: str = 'osu', default_color: Optional[int] = None, limit: int = 5):
    _require_discord()

    @app_commands.command(name=name, description=description)
    async def recent(interaction: 'discord.Interaction', user: str):
        await interaction.response.defer(thinking=True)
        bot_client = get_bot_client(interaction)
        result = await _maybe_await(bot_client.aget_recent_plays(user, mode=mode, include_fails=include_fails, limit=limit))
        await interaction.followup.send(embed=_embed_from_payload(result.to_embed_payload(color=default_color)))

    return recent


def create_command_bundle(*, get_bot_client: Callable[[Any], Any], mode: str = 'osu', default_color: Optional[int] = None, top_limit: int = 5, recent_limit: int = 5) -> dict[str, Any]:
    return {
        'current': create_current_command(get_bot_client=get_bot_client, mode=mode, default_color=default_color),
        'recent': create_recent_command(get_bot_client=get_bot_client, mode=mode, default_color=default_color, limit=recent_limit),
        'profile': create_profile_command(get_bot_client=get_bot_client, mode=mode, default_color=default_color),
        'top': create_top_command(get_bot_client=get_bot_client, mode=mode, default_color=default_color, limit=top_limit),
        'fails': create_fails_command(get_bot_client=get_bot_client, mode=mode, default_color=default_color),
        'map': create_map_command(get_bot_client=get_bot_client, default_color=default_color),
        'compare': create_compare_command(get_bot_client=get_bot_client, mode=mode, default_color=default_color),
    }

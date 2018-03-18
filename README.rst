============
Red-Lavalink
============

A Lavalink client library written for Python 3.5 using the AsyncIO framework.
This library may be used for other projects as it contains no Red specific code or logic.

However, it is important to note that this library only supports projects using discord.py.

To install::

    pip install red-lavalink

*****
Usage
*****

.. code-block:: python

    import lavalink
    from discord.ext.commands import Bot

    bot = Bot()


    @bot.event
    async def on_ready():
        lavalink.initialize(
            bot, host='localhost', password='password',
            rest_port=2332, ws_port=2333
        )


    async def search_and_play(voice_channel, search_terms):
        player = await lavalink.connect(voice_channel)
        tracks = await player.search_yt(search_terms)
        player.add(tracks[0])
        await player.play()

When shutting down, be sure to do the following::

    await lavalink.close()

============
Red-Lavalink
============

.. image:: https://api.travis-ci.org/Cog-Creators/Red-Lavalink.svg?branch=develop
    :target: https://travis-ci.org/Cog-Creators/Red-Lavalink
    :alt: Travis CI status

.. image:: https://readthedocs.org/projects/red-lavalink/badge/?version=latest
    :target: http://red-lavalink.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
    
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black
    :alt: Code style: black

A Lavalink client library written for Python 3.8 using the AsyncIO framework.
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

*********
Shuffling
*********
.. code-block:: python

    def shuffle_queue(player_id, forced=True):
        player = lavalink.get_player(player_id)
        if not forced:
            player.maybe_shuffle(sticky_songs=0)
            """
            `player.maybe_shuffle` respects `player.shuffle`
            And will only shuffle if `player.shuffle` is True.

            `player.maybe_shuffle` should be called every time
            you would expect the queue to be shuffled.

            `sticky_songs=0` will shuffle every song in the queue.
            """
        else:
            player.force_shuffle(sticky_songs=3)
            """
            `player.force_shuffle` does not respect `player.shuffle`
            And will always shuffle the queue.

            `sticky_songs=3` will shuffle every song after the first 3 songs in the queue.
            """




When shutting down, be sure to do the following::

    await lavalink.close()

import os
import random
from wavelink.ext import spotify
from nextcord.ext import commands
import nextcord
import wavelink
from dotenv import load_dotenv
from pathlib import Path

#getting valids from env file
dotenv_path = Path("token.env")
load_dotenv(dotenv_path=dotenv_path)
TOKEN = os.getenv('DISCORD_TOKEN')
spotiy_secret = os.getenv("SPOTIFY_SECRET")
spotiy_id = os.getenv("SPOTIFY_ID")

#define command sign and intents of the bot
client = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

class CustomPlayer(wavelink.Player):

    #initiating bot class
    def __init__(self):
        print("Creating custom player class...")
        super().__init__()

        #modes of bot
        self.queue = wavelink.Queue()
        self.shuffle = False
        self.loop = False
        self.loopq = False
        self.loopq_list = []
        self.looped_track = ""
        self.skipto = 0
        self.spotify_playlist = 0


# HTTPS and websocket operations
@client.event
async def on_ready():
    client.loop.create_task(connect_nodes())

# login to lavalink server
async def connect_nodes():
    await client.wait_until_ready()
    print("Connecting to the node")
    await wavelink.NodePool.create_node(bot=client, host="host", port=0000, password="pasw", spotify_client=spotify.SpotifyClient(client_id=spotiy_id, client_secret=spotiy_secret))

# print on bot connect to node
@client.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f'Node: <{node.identifier}> is ready!')

#how to handle playing next track in q
@client.event
async def on_wavelink_track_end(player: CustomPlayer, track: wavelink.Track, reason):

    if not player.queue.is_empty:

        if player.loop == True:
            await player.play(player.looped_track)
            return

        next_track = player.queue.get()
        await player.play(next_track)

        if player.skipto != 0:
            await player.seek(player.track.length * 1000)
            player.skipto = player.skipto - 1
            return

    #not really working rn...
    if player.loopq == True:
        player.queue = player.loopq_list
        next_track = player.queue.get()
        await player.play(next_track)

# commands
@client.command()
async def connect(ctx):
    vc = ctx.voice_client # represents a discord voice connection
    try:
        channel = ctx.author.voice.channel
    except AttributeError:
        return await ctx.send("Please join a voice channel to connect.")

    if not vc:
        await ctx.author.voice.channel.connect(cls=CustomPlayer())
    else:
        await ctx.send("The bot is already connected to a voice channel")

# disconnect command
@client.command()
async def dc(ctx):
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")

# play command for youtube and spotify single track and playlists/albums
@client.command()
async def play(ctx, *, search: str):
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)

    # Youtube playlist process
    if search.find("&list") != -1 or search.find("?list") != -1:

        found_song = await wavelink.YouTubePlaylist.search(query=search)

        if vc.is_playing():

            for _ in found_song.tracks:
                vc.queue.put(item=_)

            await ctx.send(embed=nextcord.Embed(
                title="Playlist zařazen do Q"
            ))

        else:             
            await vc.play(found_song.tracks[0])

            for i in range(1,len(found_song.tracks)):
                vc.queue.put(item=found_song.tracks[i])

            if vc.loop == True:
                vc.looped_track = found_song.tracks[0]

        return

    #Spotify processing
    if search.find("spotify.com/") != -1:

        #check if the url is for playlist
        if search.find("playlist") != -1 or search.find("album") != -1:
            
            print("spotify playlist rq...")

            async for partial in spotify.SpotifyTrack.iterator(query=search, partial_tracks=True):
                vc.queue.put(partial)

            if vc.shuffle == True:
                random.shuffle(vc.queue)

            if vc.is_playing():
                await ctx.send(embed=nextcord.Embed(
                    title="Playlist zařazen do Q"
                ))

            else:
                next_track = vc.queue.get()
                await vc.play(next_track)

                await ctx.send(embed=nextcord.Embed(
                    title=vc.source.title,
                    url=vc.source.uri,
                    description=f"Právě přehrávám tuto pecku : {vc.source.title}"
                ))

                if vc.loop == True:
                    vc.looped_track = next_track
        
        #spotify single track part
        else:
            track = await spotify.SpotifyTrack.search(query=search, return_first=True)

            print("spotify track qued")

            if vc.is_playing():
                vc.queue.put(item=track)

                await ctx.send(embed=nextcord.Embed(
                    title=track.title,
                    url=track.uri,
                    description=f"Zařazeno {track.title}"
                ))

            else:

                await vc.play(track)

                await ctx.send(embed=nextcord.Embed(
                    title=vc.source.title,
                    url=vc.source.uri,
                    description=f"Právě přehrávám tuto pecku : {vc.source.title}"
                ))

    #Youtube single track
    else:
        found_song = await wavelink.YouTubeTrack.search(query=search, return_first=True)

        print("Youtube st")
    
        if vc.is_playing():

            vc.queue.put(item=found_song)

            await ctx.send(embed=nextcord.Embed(
                title=found_song.title,
                url=found_song.uri,
                description=f"Zařazeno {found_song.title}"
            ))

        else:
            await vc.play(found_song)

            await ctx.send(embed=nextcord.Embed(
                title=vc.source.title,
                url=vc.source.uri,
                description=f"Právě přehrávám tuto pecku : {vc.source.title}"
            ))

            if vc.loop == True:
                vc.looped_track = found_song

#skip command
@client.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc:

        print("skip command")

        if not vc.is_playing():
            return await ctx.send("Nic vám tu nehraje debílci :)")
        if vc.queue.is_empty:
            await ctx.send("Dohráli jsme borci...")
            return await vc.stop()

        await vc.seek(vc.track.length * 1000)

        if vc.is_paused():
            await vc.resume()
    else:
        await ctx.send("Napoj mě někam kurva :)")

#pause command... working so far
@client.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc:

        print("Pause command")

        if vc.is_playing() and not vc.is_paused():
            await vc.pause()
        else:
            await ctx.send("Nic vám tu nehraje debílci :)")
    else:
        await ctx.send("Napoj mě někam kurva :)")

#resume command... working too :D
@client.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc:

        print("resume command")

        if vc.is_paused():
            await vc.resume()
        else:
            await ctx.send("Však vole... tu nic nemáte pauznuté... tak coje?")
    else:
        await ctx.send("Napoj mě někam kurva :)")

#TODO make the embed better somehow... but fix functions first :D
@client.command()
async def q(ctx):
    vc = ctx.voice_client
    if vc:

        print("printing queue")

        if vc.is_playing() or vc.track != None:

            description = ""
            for i in range(0, len(vc.queue)):
                if isinstance(vc.queue[i], wavelink.tracks.PartialTrack):
                    return await ctx.send(embed=nextcord.Embed(
                        title=f"Teď hraje : {vc.track.title}",
                        description=f"A dalších {len(vc.queue)}, které by trvalo moc dlouho loadovat...",
                        url=vc.track.uri))

            for i in range(0, len(vc.queue)):
                description = description + f"{i + 1} -- {vc.queue[i]}\n"

            await ctx.send(embed=nextcord.Embed(
                title=f"Teď hraje : {vc.track.title}",
                description=description,
                url=vc.track.uri))

        else:
            await ctx.send("Nic vám tu nehraje debílci :)")

    else:
        await ctx.send("Napoj mě někam kurva :)")

#not working at all.. dont know why yet
@client.command()
async def loopq(ctx):
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)

    if vc.loopq == True:

        print("unlooping q")
        vc.loopq = False
        vc.loopq_list = vc.loopq_list.clear()
        await ctx.send("Loop Q mode OFF")
        return

    print("looping q")
    vc.loopq = True
    vc.loopq_list = vc.queue.copy()
    await ctx.send("Loop Q mode ON")

#this shit is finally wokring after so much fucking time... .shuffle() is a lie
@client.command()
async def shuffle(ctx):
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)

    if vc.is_playing():

        print("shuffle command")

        testq = vc.queue.copy()
        testq.clear()
        while testq.count <= vc.queue.count:
            item = vc.queue[random.randint(0, vc.queue.count - 1)]
            if item in testq and testq.count != vc.queue.count:
                pass

            elif testq.count == vc.queue.count:
                break

            else:
                testq.put(item)

        vc.queue = testq

        await ctx.send("Šaflt")

#clear queue... works
@client.command()
async def clear(ctx):
    vc = ctx.voice_client
    if vc:

        print("cleared queue")

        vc.queue.clear()
        await ctx.send("Vyčištěno :)")

    else:
        await ctx.send("Napoj mě někam kurva")

#works.. sometimes without wanting to tho xD
@client.command()
async def loop(ctx):
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        print(ctx.author)
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)

    if vc.loop == True:
        vc.loop = False
        await ctx.send("Loop track mode OFF")
        return

    if vc.is_playing():

        print("looped track")

        vc.looped_track = vc.track
        await ctx.send("Loop track mode ON")
        return

    await ctx.send("Loop track mode ON")

    vc.loop = True

#idk if thsi works tbhh
@client.command()
async def playnext(ctx, *, search: wavelink.YouTubeTrack):
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)

    if vc.is_playing():

        print("playnext command")

        vc.queue.put_at_front(item=search)

        await ctx.send(embed=nextcord.Embed(
            title=search.title,
            url=search.uri,
            description=f"Další pecka bude : {search.title}"
        ))
        return

    await vc.play(search)

    await ctx.send(embed=nextcord.Embed(
        title=vc.source.title,
        url=vc.source.uri,
        description=f"Právě přehrávám tuto pecku : {vc.source.title}"
    ))

    if vc.loop == True:
        vc.looped_track = search

# this doesnt work I think
@client.command()
async def skipto(ctx, *, search: int):
    vc = ctx.voice_client
    if vc:
        if not vc.is_playing():
            return await ctx.send("Nic vám tu nehraje debílci :)")
        if vc.queue.is_empty:
            await ctx.send("Tak jsi koště?")
            return await vc.stop()

        print("skipto command")

        vc.skipto = search - 1
        await vc.seek(vc.track.length * 1000)

        if vc.is_paused():
            await vc.resume()
    else:
        await ctx.send("Napoj mě někam kurva :)")

#error handling... well this works so far
@play.error
async def play_error(ctx, error):
    if isinstance(error, commands.BadArgument):
       await ctx.send("Could not find a track.")
    else:
       await ctx.send("Please join a voice channel.")


client.run(TOKEN)

import discord
from discord.ext import commands
import ffmpeg
import json
import asyncio
import datetime

from youtube_dl import YoutubeDL


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # all the music related stuff
        self.is_playing = False
        self.is_paused = False
        self.q_position = 0
        self.vbay_color = 12429840


        # 2d array containing [song, channel]
        self.music_queue = []
        self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                               'options': '-vn'}

        self.vc = None


    async def open_account(self, user):
        users = await self.get_playlist()


        if str(user.id) in users:
            return False
        else:
            users[str(user.id)] = {}

        with open("playlist.json", "w") as f:
            json.dump(users, f)
            return True



    async def get_playlist(self):
        with open("playlist.json", "r") as f:
            users = json.load(f)

        return users

    @commands.command(name="create-playlist", aliases=["cp"], help="Create A Playlist")
    async def create_playlist(self, ctx, *args):
        await self.open_account(ctx.author)

        users = await self.get_playlist()

        playlist_name = " ".join(args)


        if playlist_name == '':
            error = discord.Embed(title="Error", description="Usage: !create-playlist [name of playlist]", color = discord.Color.dark_red())
            await ctx.send(embed = error)
            return

        if playlist_name in users[str(ctx.author.id)]:
            em = discord.Embed(title="Error", description="There is already a playlist with that name", color = discord.Color.dark_red())

            await ctx.send(embed = em)
            return

        users[str(ctx.author.id)][playlist_name] = []

        with open("playlist.json", "w") as f:
            json.dump(users, f)

        created = discord.Embed(title="Playlist Created", color = self.vbay_color)
        created.add_field(name="Name", value = playlist_name)
        created.add_field(name="Current Songs", value = 0)

        await ctx.send(embed=created)

        return

    class playlist_dropdown(discord.ui.Select):
        def __init__(self, ctx, music_cog, users):
            # Set the options that will be presented inside the dropdown
            self.ctx = ctx
            self.music_cog = music_cog
            self.users = users
            self.playlist_list = []
            for i in self.users[str(self.ctx.author.id)]:
                self.playlist_list.append(discord.SelectOption(label=str(i), value = str(i)))

            # The placeholder is what will be shown when no option is chosen
            # The min and max values indicate we can only pick one of the three options
            # The options parameter defines the dropdown options. We defined this above
            super().__init__(placeholder='Choose a playlist', min_values=1, max_values=1, options=self.playlist_list)

        async def callback(self, interaction: discord.Interaction):

            em = discord.Embed(title = self.values[0], color=self.music_cog.vbay_color)
            song_list = []
            for i in self.users[str(self.ctx.author.id)][self.values[0]]:
                song_list.append(i)
            songs = "\n".join(song_list)
            if songs == "":
                em.add_field(name = "Songs", value = "No songs in this playlist")
            else:
                em.add_field(name='Songs', value=songs)
            await interaction.response.edit_message(embed=em)


    class playlist_view(discord.ui.View):
        def __init__(self, ctx, music_cog, users):
            super().__init__()
            self.ctx = ctx
            self.music_cog = music_cog
            self.users = users
            playlist_dropdown = self.music_cog.playlist_dropdown(self.ctx, self.music_cog, self.users)
            self.add_item(playlist_dropdown)
            '''
            self.playlist_dropdown= discord.ui.Select(options=self.playlist_list, placeholder="Choose a playlist")
            self.playlist_dropdown.callback(self.callback)
            self.add_item(self.playlist_dropdown)'''






    @commands.command(name="my-playlists", aliases=["mp"], help="Shows All The Playlists You Have")
    async def my_playlist(self, ctx):
        await self.open_account(ctx.author)
        users = await self.get_playlist()
        playlist_view = self.playlist_view(ctx, self, users)

        await ctx.send(view = playlist_view, ephemeral=True)
    class add_playlist_dropdown(discord.ui.Select):
        def __init__(self, ctx, music_cog, users, song):
            # Set the options that will be presented inside the dropdown
            self.ctx = ctx
            self.music_cog = music_cog
            self.users = users
            self.song = song
            self.playlist_list = []
            for i in self.users[str(self.ctx.author.id)]:
                self.playlist_list.append(discord.SelectOption(label=str(i), value = str(i)))

            # The placeholder is what will be shown when no option is chosen
            # The min and max values indicate we can only pick one of the three options
            # The options parameter defines the dropdown options. We defined this above
            super().__init__(placeholder='Choose a playlist', min_values=1, max_values=1, options=self.playlist_list)


        async def callback(self, interaction: discord.Interaction):
            self.users[str(self.ctx.author.id)][self.values[0]].append(self.song)

            em = discord.Embed(title = "Song added", color=self.music_cog.vbay_color)
            self.disabled = True
            self.disabled_view = self.music_cog.add_playlist_view(self.ctx, self.music_cog, self.users, self.song)

            await interaction.response.edit_message(embed=em, view = self.disabled_view)

            with open("playlist.json", "w") as f:
                json.dump(self.users, f)
                return True

    class add_playlist_view(discord.ui.View):
        def __init__(self, ctx, music_cog, users, song):
            super().__init__()
            self.ctx = ctx
            self.music_cog = music_cog
            self.users = users
            self.song = song
            self.playlist_dropdown = self.music_cog.add_playlist_dropdown(self.ctx, self.music_cog, self.users, self.song)
            self.add_item(self.playlist_dropdown)


    @commands.command(name = 'add-playlist-song', aliases = ['add-song', 'aps', "atp", "add-to-playlist"], help="Add a song to the playlist of your choice")
    async def add_playlist_song(self, ctx, *args):
        song_name = " ".join(args)
        await self.open_account(ctx.author)
        users = await self.get_playlist()

        if song_name == '':
            error = discord.Embed(title="Error", description="Usage: !create-playlist [name of song]", color = discord.Color.dark_red())
            await ctx.send(embed = error)
            return

        song = self.search_yt(song_name)
        if type(song) == type(True):
            await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
            return
        playlist_view = self.add_playlist_view(ctx, self, users, song_name)
        await ctx.send(view = playlist_view, ephemeral=True)


    class add_queue_dropdown(discord.ui.Select):
        def __init__(self, ctx, music_cog, users):
            # Set the options that will be presented inside the dropdown
            self.ctx = ctx
            self.music_cog = music_cog
            self.users = users
            self.playlist_list = []
            for i in self.users[str(self.ctx.author.id)]:
                self.playlist_list.append(discord.SelectOption(label=str(i), value = str(i)))

            # The placeholder is what will be shown when no option is chosen
            # The min and max values indicate we can only pick one of the three options
            # The options parameter defines the dropdown options. We defined this above
            super().__init__(placeholder='Choose a playlist', min_values=1, max_values=1, options=self.playlist_list)


        async def callback(self, interaction: discord.Interaction):
            for i in self.users[str(self.ctx.author.id)][self.values[0]]:
                await self.music_cog.play(self.ctx, i)
            return







    class add_queue_view(discord.ui.View):
        def __init__(self, ctx, music_cog, users):
            super().__init__()
            self.ctx = ctx
            self.music_cog = music_cog
            self.users = users
            playlist_dropdown = self.music_cog.add_queue_dropdown(self.ctx, self.music_cog, self.users)
            self.add_item(playlist_dropdown)


    @commands.command(name="add-playlist-to-queue", aliases=['add-to-queue', 'atq'], help = "add a playlist to the queue")
    async def add_playlist_to_queue(self, ctx):
        await self.open_account(ctx.author)

        users = await self.get_playlist()
        add_queue_view = self.add_queue_view(ctx, self, users)
        await ctx.send(view=add_queue_view, ephemeral=True)





    # searching the item on youtube
    def search_yt(self, item):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info("ytsearch:%s" % item, download=False)['entries'][0]
            except Exception:
                return False

        format_duration = str(datetime.timedelta(seconds=(int(info['duration']))))
        return {'source': info['formats'][0]['url'], 'title': info['title'], 'duration': format_duration}

    def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True

            # get the first url
            m_url = self.music_queue[0][0]['source']

            # remove the first element as you are currently playing it
            self.music_queue.pop(0)


            self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False

    # infinite loop checking
    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True

            m_url = self.music_queue[0][0]['source']

            # try to connect to voice channel if you are not already connected
            if self.vc == None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

                # in case we fail to connect
                if self.vc == None:
                    await ctx.send("Could not connect to the voice channel")
                    return
            else:
                await self.vc.move_to(self.music_queue[0][1])

            # remove the first element as you are currently playing it
            self.music_queue.pop(0)

            self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS),  after=lambda e: self.play_next())
        else:
            self.is_playing = False

    @commands.command(name="play", aliases=["p", "playing"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        query = " ".join(args)
        try:
            voice_channel = ctx.author.voice.channel
        except:
            error = discord.Embed(title="Error", description="Please connect to a voice channel", color = discord.Color.dark_red())
            await ctx.send(embed = error)
            return

        if self.is_paused:
            self.vc.resume()
        else:
            song = self.search_yt(query)
            if type(song) == type(True):
                error_embed = discord.Embed(title="Error", description = "Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.", color = discord.Color.dark_red())
            else:
                self.music_queue.append([song, voice_channel])

                em = discord.Embed(title= "Song added to queue", description = str(self.music_queue[0][0]['title']), color = self.vbay_color)

                em.set_author(name=("Requested by: " + str(ctx.author.name)), icon_url= ctx.author.avatar)
                await ctx.send(embed = em)

                if self.is_playing == False:
                    await self.play_music(ctx)

    @commands.command(name="pause", help="Pauses the current song being played")
    async def pause(self, ctx, *args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
        elif self.is_paused:
            self.vc.resume()

    @commands.command(name="resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx, *args):
        if self.is_paused:
            self.vc.resume()

    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        if self.vc != None and self.vc:
            self.vc.stop()


    class QueueView(discord.ui.View):
        def __init__(self, music_cog, ctx):
            super().__init__()
            self.vbay_color = 12429840

            self.q_pos = 0
            self.queue = music_cog.music_queue
            self.music_cog = music_cog
            self.ctx = ctx


        @discord.ui.button(label='Back', style=discord.ButtonStyle.blurple)
        async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.q_pos -= 1
            em = discord.Embed(color = self.vbay_color, title = str(self.queue[self.q_pos][0]['title']))
            em.add_field(name="Duration", value=str(self.queue[self.q_pos][0]['duration']))

            if self.q_pos == 0:
                self.back.disabled = True
            if self.q_pos != len(self.queue):
                self.next.disabled = False



            await interaction.response.edit_message(embed=em, view=self)
        @discord.ui.button(label='Next', style=discord.ButtonStyle.blurple)
        async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.q_pos += 1
            em = discord.Embed(color=self.vbay_color, title=str(self.queue[self.q_pos][0]['title']))
            em.add_field(name="Duration", value=str(self.queue[self.q_pos][0]['duration']))

            if self.q_pos+1 == len(self.queue):
                self.next.disabled = True
            if self.q_pos != 0:
                self.back.disabled = False

            await interaction.response.edit_message(embed=em, view=self)

        @discord.ui.button(label="Skip", style = discord.ButtonStyle.blurple)
        async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.music_cog.vc != None and self.music_cog.vc:
                self.music_cog.vc.stop()
                await asyncio.sleep(2)
            self.back.disabled = True
            if len(self.queue) == 1:
                self.next.disabled = True
            if len(self.queue) != 0:
                self.q_pos = 0
                em = discord.Embed(color=self.vbay_color, title=str(self.queue[self.q_pos][0]['title']))
                em.add_field(name="Duration", value=str(self.queue[self.q_pos][0]['duration']))

                await interaction.response.edit_message(embed=em, view=self)
            else:
                em = discord.Embed(title="No music in queue", color=discord.Color.dark_red())
                await interaction.response.edit_message(embed=em, view=None)

        @discord.ui.button(label="Remove", row=2, style = discord.ButtonStyle.danger)
        async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.music_cog.music_queue.pop(self.q_pos)
            self.back.disabled = True
            if len(self.queue) == 1:
                self.next.disabled = True
            if len(self.queue) != 0:
                self.q_pos = 0
                em = discord.Embed(color=self.vbay_color, title=str(self.queue[self.q_pos][0]['title']))
                em.add_field(name="Duration", value=str(self.queue[self.q_pos][0]['duration']))

                await interaction.response.edit_message(embed=em, view=self)
            else:
                em = discord.Embed(title="No music in queue", color=discord.Color.dark_red())
                await interaction.response.edit_message(embed=em, view=None)

        @discord.ui.button(label = "Add To Playlist", row=2, style=discord.ButtonStyle.success)
        async def add_to_playlist(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.music_cog.open_account(self.ctx.author)
            users = await self.music_cog.get_playlist()
            song = self.music_cog.music_queue[self.q_pos][0]['title']

            add_playlist_view = self.music_cog.add_playlist_view(self.ctx, self.music_cog, users, song)
            await interaction.response.send_message(view=add_playlist_view, ephemeral=True)




    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        retval = ""
        id = ctx.guild.id
        print(id)

        queue_view = self.QueueView(self, ctx)

        queue_view.back.disabled=True
        if len(self.music_queue) == 1:
            queue_view.next.disabled = True
        if len(self.music_queue) != 0:
            em = discord.Embed(title = self.music_queue[self.q_position][0]['title'], color = self.vbay_color)
            em.add_field(name="Duration", value=str(self.music_queue[0][0]['duration']))

            await ctx.send(embed=em, view = queue_view)
        else:
            em = discord.Embed(title="No music in queue", color = discord.Color.dark_red())
            await ctx.send(embed = em)

    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        if self.vc != None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        await ctx.send("Music queue cleared")

    @commands.command(name="leave", aliases=["disconnect", "l", "dc"], help="Kick the bot from VC")
    async def dc(self, ctx):
        self.is_playing = False
        self.is_paused = False
        if self.vc != None and self.is_playing:
            self.vc.stop()
        self.music_queue = []

        await self.vc.disconnect()

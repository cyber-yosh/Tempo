import discord
import asyncio
from discord.ext import commands
import ffmpeg
from music_cog import music_cog



bot = commands.Bot(command_prefix="$", intents = discord.Intents.all())

@bot.event
async def on_ready():
    activity = discord.Game(name="$help", type=3)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print("Bot is ready!")



async def load_extensions():
    await bot.add_cog(music_cog(bot))



#remove the default help command so that we can write out own


#register the class with the bot
asyncio.run(load_extensions())


bot.run("OTk5ODYyNjMyMDY2NTg0Njc5.GKZAJZ.eSwckeL4Mt5MQc0zyYgmo3XRrzkugDifkMy-yM")

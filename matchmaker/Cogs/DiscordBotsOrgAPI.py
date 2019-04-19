'''
Created on 17.04.2019

@author: Joshua Esselmann
'''
import dbl
import discord
from discord.ext import commands

import aiohttp
import asyncio
import os


class DiscordBotsOrgAPI(commands.Cog):
    """Handles interactions with the discordbots.org API"""
    
    TOKEN_FILE = "dbl_token.txt"
    COG_NAME = "DiscordBotsOrgAPI"
    
    def __init__(self, bot):
        self.bot = bot
        self.controller = self.bot.get_cog('Controller')
        
        if os.path.exists(self.TOKEN_FILE):
            with open(self.TOKEN_FILE) as f:
                self.token = f.readline()
        
            self.dblpy = dbl.Client(self.bot, self.token, loop=self.bot.loop)
        else:
            self.controller._print("DBL_API",'Not loaded.', cog=self.COG_NAME)
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.update_stats())
    
    async def update_stats(self):
        """This function runs every 30 minutes to automatically update your server count"""

        while not self.bot.is_closed():
            self.controller._print("DBL_API",'attempting to post server count', cog=self.COG_NAME)
            try:
                await self.dblpy.post_server_count()
                self.controller._print("DBL_API",'posted server count ({})'.format(len(self.bot.guilds)), cog=self.COG_NAME)
            except Exception as e:
                self.controller._print("DBL_API",'Failed to post server count\n{}: {}'.format(type(e).__name__, e), cog=self.COG_NAME)
            await asyncio.sleep(1800)


def setup(bot):
    bot.add_cog(DiscordBotsOrgAPI(bot))
'''
Created on 09.04.2019

@author: Joshua Esselmann
'''
from discord.ext import commands

class CoinTournament(commands.Cog):
    '''
    classdocs
    '''
    testVar = "hi"

    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('Cog CoinTournament loaded')
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send('Welcome {0.mention}.'.format(member))

    @commands.command()
    async def testdebug(self, ctx):
        """Says hello"""
        member = ctx.author
        server = ctx.guild.id
        await ctx.send(self.testVar)
    
def setup(bot):
    bot.add_cog(CoinTournament(bot))
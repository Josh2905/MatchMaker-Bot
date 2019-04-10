'''
Created on 09.04.2019

@author: Joshua Esselmann
'''
from discord.ext import commands
import asyncio

class CoinTournament(commands.Cog):
    '''
    classdocs
    '''
    class ServerNode():
        '''This class is used to store variables for each connected Server.'''
        
        def __init__(self, _id):
            self.id = _id
            self.msgCounter = 0
            self.activeMessage = False
            
    
    testVar = "hi"
    SERVER_VARS = {}
    init = False
    
    def __init__(self, bot):
        self.bot = bot
        
    
    @commands.Cog.listener()
    async def on_ready(self):
        controller = self.bot.get_cog('TestCog')
        
        for server in self.bot.guilds:
            self.SERVER_VARS[server.id] = self.ServerNode(server.id)
        
        print('Cog CoinTournament loaded')
        self.init = True
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send('Welcome {0.mention}.'.format(member))
    
    @commands.Cog.listener()
    async def on_message(self, message):
        mainCog = self.bot.get_cog('TestCog')
        if mainCog.init:
        
            print('asdfss')
            print(mainCog.SERVER_VARS[message.guild.id].commandTimeout)
            print('asdf')
    
    @commands.command()
    async def testdebug(self, ctx):
        """Says hello"""
        member = ctx.author
        server = ctx.guild.id
        controller = self.bot.get_cog('TestCog')
        await ctx.send(controller.testVar)
        
class TestCog(commands.Cog):
    '''
    classdocs
    '''
    class ServerNode():
        '''This class is used to store variables for each connected Server.'''
        
        def __init__(self, _id):
            self.id = _id
            self.commandTimeout = False
            self.checkTimeout = False
            self.repostMessage = False
    
    
    testVar = False
    SERVER_VARS = {}
    init = False
    
    def __init__(self, bot):
        self.bot = bot
        self.controller = self.bot.get_cog('CoinTournament')
    
    @commands.Cog.listener()
    async def on_ready(self):
        
        for server in self.bot.guilds:
            self.SERVER_VARS[server.id] = self.ServerNode(server.id)
        
        print('Cog TestCog loaded')
        self.init = True
        
    @commands.Cog.listener()
    async def on_message(self, message):
        print('MESSAGE')
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send('Welcome {0.mention}.'.format(member))

    @commands.command()
    async def test12(self, ctx):
        """Says hello"""
        member = ctx.author
        server = ctx.guild.id
        await ctx.send(self.controller.testVar)
    
def setup(bot):
    bot.add_cog(CoinTournament(bot))
    bot.add_cog(TestCog(bot))
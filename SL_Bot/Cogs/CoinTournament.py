'''
Created on 09.04.2019

@author: Joshua Esselmann
'''
from discord.ext import commands
import asyncio

class CoinTournament(commands.Cog):
    '''Implements functionality of a coin based tournament.
    '''
    class ServerNode():
        '''This class is used to store variables for each connected Server.'''
        
        def __init__(self, _id):
            self.id = _id
            
            
    SERVER_VARS = {}
    COG_NAME = "CoinTournament"
    initialized = False
    
    def __init__(self, bot):
        self.bot = bot
        self.controller = self.bot.get_cog('Controller')
        
        if True:
            pass
    
    #===============================================================================
    # called in on_ready of controller  
    #===============================================================================
    
    async def initialize(self):
        self.controller._print("init",'initializing CoinTournament', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME)
            
        self.controller._print("init",'initialize server variables', cog=self.COG_NAME)
        
        for server in self.bot.guilds:
            self.SERVER_VARS[server.id] = self.ServerNode(server.id)
        
        self.controller._print("init",'------', cog=self.COG_NAME)
        
        self.initialized = True
        
        self.controller._print("init",'Cog Initialized', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME)
         
    async def init_on_error(self):
        self.initialized = False
        self.controller._print("init",'initializing CoinTournament after error', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME)
        
        self.initialized = True
        
        self.controller._print("init",'Cog Initialized', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME)
        
        if True:
            pass
    
    
    @commands.command()
    async def testdebug(self, ctx):
        """Says hello"""
        member = ctx.author
        server = ctx.guild.id
        
        await ctx.send("TEST")
    
def setup(bot):
    bot.add_cog(CoinTournament(bot))
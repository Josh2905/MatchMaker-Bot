'''
Created on 10.04.2019

@author: Joshua Esselmann
'''
from discord.ext import commands
from random import randint

class Misc(commands.Cog):
    '''
    Implements miscellaneous features.
    '''
    
    class ServerNode():
        '''This class is used to store variables for each connected Server.'''
        
        def __init__(self, _id):
            self.id = _id
            
    SERVER_VARS = {}
    COG_NAME = "Misc"
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
        self.controller._print("init",'initializing Misc', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME)
            
        #self.controller._print("init",'initialize server variables', cog=self.COG_NAME)
        
        #for server in self.bot.guilds:
            #self.SERVER_VARS[server.id] = self.ServerNode(server.id)
        
        #self.controller._print("init",'------', cog=self.COG_NAME)
        
        self.initialized = True
        
        self.controller._print("init",'Cog Initialized', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME)
         
    async def init_on_error(self):
        self.controller._print("init",'initializing MatchMaking', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME)
        
        self.initialized = True
        
        self.controller._print("init",'Cog Initialized', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME)
        
        if True:
            pass
    
    #===============================================================================
    # Commands
    #===============================================================================
    
    @commands.command()
    async def roll(self, ctx, *args):
        '''Command to roll a random number between 1 and 9.
        
        :param ctx: context of command call
        '''
        
        user = ctx.message.author
        message = ctx.message
        server = ctx.message.guild.id
        
        self.controller._print(server, str(user.name) + ":" + str(user.id) + " used command: roll ", cog=self.COG_NAME)
        
        randInt = randint(0, 9)
        await message.channel.send("{} hat eine **".format(user.mention) + str(randInt) + "** gewürfelt.")
        # await message.delete()
        
def setup(bot):
    bot.add_cog(Misc(bot))
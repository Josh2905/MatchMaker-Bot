'''
Created on 09.04.2019

@author: Joshua Esselmann
'''
import asyncio
import datetime

import json
import os
from collections import deque
from random import randint
from functools import partial
import logging
import traceback
from logging.handlers import TimedRotatingFileHandler


import discord
from discord.ext import commands
from discord.utils import get
from SL_Bot.ServerNode import serverNode

class Controller(commands.Cog):
    '''
    classdocs
    '''
    
    ####################################################################################################
    ##DEFAULTS##
    ####################################################################################################
    VERSION = "1.1.2"
    
    AUTHOR_ID = 90043934247501824
    SETTINGS_FILE = 'settings.json'
    TOKEN_FILE = 'token.txt'
    
    MAINCHANNEL = ''                  # right click on channel and select "copy ID"
    PREFIX = "!"
    
    ##Repeated message##
    
    # if messages are sent too quickly, the actual number might be off by 1 or 2.
    MESSAGE_INTERVAL = 20
                                    
    MESSAGE_CONTENT = "Reagiert mit :ok_hand: für 1vs1, :joy: für 2vs2. \nReagiert erneut, um die Rollen wieder zu entfernen.\nAlternativ könnt ihr euch die Rollen auch mit $1vs1 bzw $2vs2 geben und nehmen. \nnach 30 Minuten werden die Rollen automatisch entfernt.\n"
    
    #in seconds
    MESSAGE_REPOST_TIME = 60*5
    
    # uses unicode. if using custom emoji, use the name without ":"
    REACTION_1VS1 = "👌"
    REACTION_2VS2 = "\U0001F602"
    REACTION_CANCEL = "\u26D4"
    
    ROLE_1VS1 = ""
    ROLE_2VS2 = ""
    
    #in seconds
    ROLE_TIMEOUT = 60*30
    
    CHECK_INTERVAL_ROLES = 60
    CHECK_INTERVAL_REPOST = 60
    COMMANDS = {}
    DM_COMMANDS = {}
    ####################################################################################################
    ##END OF DEFAULTS##
    ####################################################################################################
    
    
    SERVER_VARS = {}
    SETTINGS = {}
    SERVER_COMMANDS = ["1vs1","2vs2","mainChannel","set","get","reset", "settings", "post", "commands", "help", "version", "restart"]
    SERVER_COGS = ["MatchMaking"]
    initialized = False
    
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.handlers.TimedRotatingFileHandler("../SLBot.log",'midnight', 1, 5, 'utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
        
    
    def __init__(self, bot):
        self.bot = bot
    
    def _print(self, server, message, log=True):
        '''A custom print command, that adds additional formatting to the output and also logs it with a logger.
        
        :param server: Server ID performing the action to be logged.
        :param message: String that will be logged.
        :param log: Decides, if message will be logged in a file or just the console.
        '''
        logStr = "<" + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + ">"
        serverObj = self.bot.get_guild(server)
        if serverObj:
            d = "[" + str(serverObj.name) + ":" + str(server) +"] "
            logStr += d
        else:
            d = "[" + str(server) + "]  "
            logStr += d
        logStr += str(message)
        print(logStr)
        if log:
            self.logger.info(str("APPLICATION" + d + str(message)))
        
    def init_settings(self):
        '''Loads saved settings from json file and creates a 
        file with default values if it doesnt already exist.
        '''
        
        
        #check if config file exists
        if not os.path.exists(self.SETTINGS_FILE):
             
            self._print("main","Creating settings file, using default values")
                    
            data = {
                "DEFAULTS": {
                    'PREFIX': self.PREFIX,
                    'MAINCHANNEL': self.MAINCHANNEL,
                    'MESSAGE_CONTENT': self.MESSAGE_CONTENT,
                    'MESSAGE_INTERVAL' : self.MESSAGE_INTERVAL,
                    'MESSAGE_REPOST_TIME': self.MESSAGE_REPOST_TIME,
                    'REACTION_1VS1': self.REACTION_1VS1,
                    'REACTION_2VS2': self.REACTION_2VS2,
                    'ROLE_1VS1': self.ROLE_1VS1,
                    'ROLE_2VS2': self.ROLE_2VS2,
                    'ROLE_TIMEOUT': self.ROLE_TIMEOUT,
                    'CHECK_INTERVAL_ROLES': self.CHECK_INTERVAL_ROLES,
                    'CHECK_INTERVAL_REPOST': self.CHECK_INTERVAL_REPOST,
                    'COMMANDS': self.COMMANDS,
                    'DM_COMMANDS': self.DM_COMMANDS,
                }
            }
            with open(self.SETTINGS_FILE, 'w') as configfile:
                json.dump(data, configfile, indent=4)
            
            self.SETTINGS = data
            self._print("main","Settings created successfully")
        else:
            self._print("main","Load settings from settings.json")
            with open(self.SETTINGS_FILE, "r") as read_file:
                data = json.load(read_file)
                              
                self.SETTINGS = data
            self._print("main","Settings loaded")
            
    def update_settings(self, _server, key, value, customCmd=False, customDmCmd=False):
        '''Updates settings file with new Values, loads new settings into the global settings dict.
        
        :param server: Server ID 
        :param key: Key value of settings file
        :param value: Corresponding value 
        :param customCmd: if it is a custom command or not.
        '''
        with open(self.SETTINGS_FILE, "r+") as read_file:
            data = json.load(read_file)
            
            server = str(_server)
            
            # add new setting to data, if missing
            if server not in list(data):
                newEntry = {}
                data[server] = newEntry
            
            #check if new command was added
            if customCmd:
                # add new setting to data, if missing
                if 'COMMANDS' not in list(data[server]):
                    newEntry = {}
                    data[server]['COMMANDS'] = newEntry
                
                if value == "delete":
                    data[server]['COMMANDS'].pop(customCmd, None)
                else:   
                    data[server]['COMMANDS'][customCmd] = value
            elif customDmCmd:
                # add new setting to data, if missing
                if 'DM_COMMANDS' not in list(data[server]):
                    newEntry = {}
                    data[server]['DM_COMMANDS'] = newEntry
                
                if value == "delete":
                    data[server]['DM_COMMANDS'].pop(customDmCmd, None)
                else:   
                    data[server]['DM_COMMANDS'][customDmCmd] = value
            else:
                data[server][key] = value
                
            read_file.seek(0)
            json.dump(data, read_file, indent=4)
            read_file.truncate()
            
            self.SETTINGS = data
            self._print(_server, "Settings updated: " + str(key) + " = " + str(value))
                       
    def get_setting(self, server, key):
        ''' Gets setting value from global settings dict.
        
        :param server: Server ID
        :param key: Key of Setting
        '''
        value = None
        
        if str(server) in list(self.SETTINGS) and key in list(self.SETTINGS[str(server)]):
            value = self.SETTINGS[str(server)][key]
        else:
            value = self.SETTINGS['DEFAULTS'][key]
        
        try:
            value = int(value)
        except:
            pass
        
        return value
        
    def is_command(self, cmd, server):
        '''Return, if a command with this name exists.
        
        :param cmd: Command name
        :param server: Server ID
        '''
        if len(cmd) > 1 and cmd[0] == str(self.get_setting(server, 'PREFIX')):
                
            command = cmd[1:]
            
            mainCommand = command.split(" ", 1)[0]
            
            if mainCommand in self.SERVER_COMMANDS:
                return True
        return False
    
    def is_custom_command(self, cmd, server):
        '''Return, if a custom command with this name exists.
        
        :param cmd: Command name
        :param server: Server ID
        '''
        if len(cmd) > 1 and cmd[0] == str(self.get_setting(server, 'PREFIX')):
                
            command = cmd[1:]
            
            cmdDict = self.get_setting(server, 'COMMANDS')
            
            if command in list(cmdDict):
                return True
        return False
    
    def is_custom_dmcommand(self, cmd, server):
        '''Return, if a custom dmcommand with this name exists.
        
        :param cmd: Command name
        :param server: Server ID
        '''
        if len(cmd) > 1 and cmd[0] == str(self.get_setting(server, 'PREFIX')):
                
            command = cmd[1:]
            
            cmdDict = self.get_setting(server, 'DM_COMMANDS')
            
            if command in list(cmdDict):
                return True
        return False

    async def checkPermissions(self, user, channel, creator=False):
        '''Returns, wether the user has permission to use the bots advanced features.
        
        :param user: User to be checked
        :param channel: channel the answer will be posted to
        :param creator: True, if only the creator has access
        '''
        if user.id == self.AUTHOR_ID or (not creator and user.guild_permissions.administrator):
            return True
        else:
            msg = await channel.send("{} du hast keine Rechte für diesen Befehl.".format(user.mention))
            await asyncio.sleep(3)
            await msg.delete()
            self._print(channel.guild.id, str(user.name) + ":" + str(user.id) + " didnt have permissions.")
            return False
            
    def is_me(self, m):
        '''Checks if bot is the author of a message.
        
        :param m: message to be checked.a
        '''
        return m.author == self.bot.user
        # block folding shit
        if True:
            pass

    #===============================================================================
    # looped routines    
    #===============================================================================
    
    async def commandTimeout(self, server):
        '''Periodically checks for role emoji change requests and lets them time out if unanswered.
        
        :param server: Server ID
        '''
        
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            if self.initialized and (not self.get_setting(server, 'MAINCHANNEL') == self.get_setting('DEFAULTS', 'MAINCHANNEL')):
                
                # change reaction command
                if self.SERVER_VARS[server].msg1vs1:
                    difference = datetime.datetime.utcnow() - self.SERVER_VARS[server].msg1vs1.created_at
                    self._print(server, difference)
                    if difference.total_seconds() > 60:
                        self._print(server, "1v1 reaction change timed out")
                        await self.SERVER_VARS[server].msg1vs1.delete()
                        self.SERVER_VARS[server].msg1vs1 = False
                if self.SERVER_VARS[server].msg2vs2:
                    difference = datetime.datetime.utcnow() - self.SERVER_VARS[server].msg2vs2.created_at
                    if difference.total_seconds() > 60:
                        self._print(server, "2v2 reaction change timed out")
                        await self.SERVER_VARS[server].msg2vs2.delete()
                        self.SERVER_VARS[server].msg2vs2 = False
                
            await asyncio.sleep(1000)
        
    def loadLoopRoutines(self, server):    
        '''Loads Eventloop tasks for a server.
        
        :param server: Server
        '''
        
        def callback_commandTimeout(serverID, task):
            self.SERVER_VARS[serverID].commandTimeout = False
            self._print(server.id, "commandTimeout coro stopped \n!\n!\n!")
        
        # add looped tasks to bot.
           
        if not self.SERVER_VARS[server.id].commandTimeout:
            future3 = self.bot.loop.create_task(self.commandTimeout(server.id))
            future3.add_done_callback(partial(callback_commandTimeout, server.id))
            self.SERVER_VARS[server.id].commandTimeout = True
            self._print(server.id, "commandTimeout coro created")
        
        if True:
            pass

    #===============================================================================
    # events
    #===============================================================================

    @commands.Cog.listener()
    async def on_ready(self):
        '''Executed at the startup of the bot.
        Creates initial state, adds old roles to the tracker dicts and posts main message.
        '''
        
        if not self.initialized:
            self._print("controller", '------')
            self._print("controller", 'Logged in as')
            self._print("controller", self.bot.user.name)
            self._print("controller", self.bot.user.id)
            self._print("controller", 'Version: ' + str(self.VERSION))
            self._print("controller", '------')
            
            self.init_settings()
            
            self._print("controller",'------')
            
            self._print("controller",'initialize server variables')
            
            for server in self.bot.guilds:
                self.SERVER_VARS[server.id] = serverNode(server.id)
            
            self._print("controller",'------')
            
            self._print("controller","load looped tasks")
            for server in self.bot.guilds:
                self.loadLoopRoutines(server)  
              
            self._print("controller",'------')  
            
            await self.bot.change_presence(activity=discord.Game(name='!help'))
            
            self.initialized = True
            
            self._print("controller",'Initialize Cogs') 
            
            for cogName in self.SERVER_COGS:
                cog = self.bot.get_cog(cogName)
                await cog.initialize()
                
            self._print("controller",'------')
            
        
        else:
            
            self._print("controller","load looped tasks")
            for server in self.bot.guilds:
                self.loadLoopRoutines(server)
            
            for cogName in self.SERVER_COGS:
                cog = self.bot.get_cog(cogName)
                await cog.init_on_error()
                    
            self.initialized = True
        self._print("controller",'Initialization complete')
        self._print("controller",'------')
    
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
        await ctx.send("" + self.bot.get_setting("MAINCHANNEL") + " || " + self.bot.SERVER_VARS[server])
    
def setup(bot):
    bot.add_cog(Controller(bot))
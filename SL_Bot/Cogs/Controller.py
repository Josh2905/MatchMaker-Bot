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
        
    def is_setup(self, server):
        '''Return, wether all neccessary settings are set for the bot to be fully functional.
        
        :param server: Server ID
        '''
        
        if str(server) in list(self.SETTINGS) and 'MAINCHANNEL' in list(self.SETTINGS[str(server)]) and 'ROLE_1VS1' in list(self.SETTINGS[str(server)]) and 'ROLE_2VS2' in list(self.SETTINGS[str(server)]):
            return True
        else:
            return False
    
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
        await ctx.send("" + self.bot.get_setting("MAINCHANNEL") + " || " + self.bot.SERVER_VARS[server])
    
def setup(bot):
    bot.add_cog(Controller(bot))
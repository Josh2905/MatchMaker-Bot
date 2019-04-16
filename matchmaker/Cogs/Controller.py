'''
Created on 09.04.2019

@author: Joshua Esselmann
'''

import asyncio
import datetime
import json
import os
from functools import partial
import traceback
import discord
from discord.ext import commands
from discord.utils import get

class Controller(commands.Cog):
    '''This Cog implements a general interface with common methods used in all Cogs.
    Also acts as an accessor to the settigns file.
    '''
    
    class ServerNode():
        '''This class is used to store variables for each connected Server.'''
        
        def __init__(self, _id):
            self.id = _id
            
            #bools to keep track of running coroutines
            self.commandTimeout = False
            
            self.cmdLockout = []
            
            # active commands
            self.msg1vs1 = False
            self.msg2vs2 = False
    
    
    
    ####################################################################################################
    ##DEFAULTS##
    ####################################################################################################
    VERSION = "1.2.1"
    
    AUTHOR_ID = 90043934247501824
    SETTINGS_FILE = 'settings.json'
    TOKEN_FILE = 'token.txt'
    
    GERMAN = False
    MAINCHANNEL = ''                  
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
    
    # non persistent server variables
    SERVER_VARS = {}
    # representation of settings from file
    SETTINGS = {}
    
    SERVER_COGS = ["MatchMaking", "Misc", "CoinTournament"]
    COG_NAME = "Controller"
    # is true after first on_ready call.
    initialized = False 
    
    def __init__(self, bot):
        self.bot = bot
        self.SERVER_COMMANDS = self.bot.COMMANDS
    
    def _print(self, server, message, log=True, cog=False):
        '''A custom print command, that adds additional formatting to the output and also logs it with a logger.
        
        :param server: Server ID performing the action to be logged.
        :param message: String that will be logged.
        :param log: Decides, if message will be logged in a file or just the console.
        :param cog: Adds Cog name to output string.
        '''
        logStr = "<" + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + ">"
        serverObj = self.bot.get_guild(server)
        
        if cog:
            c = "[" + str(cog) + "]"
            logStr += c
        else:
            c= ""
        
        if serverObj:
            s = "[" + str(serverObj.name) + ":" + str(server) +"] "
            logStr += s
        else:
            s = "[" + str(server) + "]  "
            logStr += s
        logStr += str(message)
        print(logStr)
        if log:
            pass
            self.bot.logger.info(str("APPLICATION" + c + s + str(message)))
        
    def init_settings(self):
        '''Loads saved settings from json file and creates a 
        file with default values if it doesnt already exist.
        '''
        
        defaults = {
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
                'GERMAN': self.GERMAN,
            }
        }
        
        #check if config file exists
        if not os.path.exists(self.SETTINGS_FILE):
             
            self._print("init","Creating settings file, using default values", cog=self.COG_NAME)
            
            with open(self.SETTINGS_FILE, 'w') as configfile:
                json.dump(defaults, configfile, indent=4)
            
            self.SETTINGS = defaults
            self._print("init","Settings created successfully", cog=self.COG_NAME)
        else:
            self._print("init","Load settings from settings.json", cog=self.COG_NAME)
            
            # update defaults.
            with open(self.SETTINGS_FILE, 'r+') as configfile:
                data = json.load(configfile)
                data["DEFAULTS"] = defaults["DEFAULTS"]
                configfile.seek(0)
                json.dump(data, configfile, indent=4)
                configfile.truncate()
            
            # load settings
            with open(self.SETTINGS_FILE, "r") as read_file:
                data = json.load(read_file)
                              
                self.SETTINGS = data
            
            self._print("init","Settings loaded", cog=self.COG_NAME)
            
    def update_settings(self, _server, key, value, customCmd=False, customDmCmd=False):
        '''Updates settings file with new Values, loads new settings into the global settings dict.
        
        :param server: Server ID 
        :param key: Key value of settings file
        :param value: Corresponding value 
        :param customCmd: if it is a custom command or not.
        :param customDmCmd: if it is a custom DM command or not.
        '''
        with open(self.SETTINGS_FILE, "r+") as read_file:
            data = json.load(read_file)
            
            server = str(_server)
            
            # add new server to data, if missing
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
            self._print(_server, "Settings updated: " + str(key) + " = " + str(value), cog=self.COG_NAME)
                       
    def get_setting(self, server, key):
        ''' Gets setting value from settings dict.
        
        Will return int if castable.
        
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
        '''Return true, if a command with this name exists.
        
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
        '''Return true, if a custom command with this name exists.
        
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
        '''Return true, if a custom dmcommand with this name exists.
        
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
        
        Right now only supports admin flag and creator.
        
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
            self._print(channel.guild.id, str(user.name) + ":" + str(user.id) + " didnt have permissions.", cog=self.COG_NAME)
            return False
    
    def is_me(self, m):
        '''Checks if bot is the author of a message.
        
        :param m: message to be checked.
        '''
        return m.author == self.bot.user
        # block folding shit
        if True:
            pass
        
    async def notify(self, channel, message, timeout=3):
        '''Send a message to the channel and delete it after a delay.
        
        :param channel: Channel to be messaged
        :param message: Message to be sent
        :param timeout: Seconds after message will be removed
        '''
        msg = await channel.send(message)
        await asyncio.sleep(timeout)
        try:
            await msg.delete()
        except:
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
                        self._print(server, "1v1 reaction change timed out", cog=self.COG_NAME)
                        await self.SERVER_VARS[server].msg1vs1.delete()
                        self.SERVER_VARS[server].msg1vs1 = False
                if self.SERVER_VARS[server].msg2vs2:
                    difference = datetime.datetime.utcnow() - self.SERVER_VARS[server].msg2vs2.created_at
                    if difference.total_seconds() > 60:
                        self._print(server, "2v2 reaction change timed out", cog=self.COG_NAME)
                        await self.SERVER_VARS[server].msg2vs2.delete()
                        self.SERVER_VARS[server].msg2vs2 = False
                
            await asyncio.sleep(1000)
        
    def loadLoopRoutines(self, server):    
        '''Loads Eventloop tasks for a server.
        
        :param server: Server
        '''
        
        def callback_commandTimeout(serverID, task):
            self.SERVER_VARS[serverID].commandTimeout = False
            self._print(server.id, "commandTimeout coro stopped \n!\n!\n!", cog=self.COG_NAME)
        
        # add looped tasks to bot.
           
        if not self.SERVER_VARS[server.id].commandTimeout:
            future3 = self.bot.loop.create_task(self.commandTimeout(server.id))
            future3.add_done_callback(partial(callback_commandTimeout, server.id))
            self.SERVER_VARS[server.id].commandTimeout = True
            self._print(server.id, "commandTimeout coro created", cog=self.COG_NAME)
        
        if True:
            pass

    #===============================================================================
    # Events
    #===============================================================================

    @commands.Cog.listener()
    async def on_ready(self):
        '''Executed at the startup of the bot.
        Creates initial state and loads the cogs.
        '''
                
        if not self.initialized:
            self._print("init", '------', cog=self.COG_NAME)
            self._print("init", 'Logged in as', cog=self.COG_NAME)
            self._print("init", self.bot.user.name, cog=self.COG_NAME)
            self._print("init", self.bot.user.id, cog=self.COG_NAME)
            self._print("init", 'Version: ' + str(self.VERSION), cog=self.COG_NAME)
            self._print("init", '------', cog=self.COG_NAME)
            
            self.init_settings()
            
            self._print("init",'------', cog=self.COG_NAME)
            
            self._print("init",'initialize server variables', cog=self.COG_NAME)
            
            for server in self.bot.guilds:
                self.SERVER_VARS[server.id] = self.ServerNode(server.id)
            
            self._print("init",'------', cog=self.COG_NAME)
            
            self._print("init","load looped tasks", cog=self.COG_NAME)
            for server in self.bot.guilds:
                self.loadLoopRoutines(server)  
              
            self._print("init",'------', cog=self.COG_NAME)  
            
            await self.bot.change_presence(activity=discord.Game(name='!help'))
            
            self.initialized = True
            
            self._print("init",'Initialize Cogs', cog=self.COG_NAME) 
            
            for cogName in self.SERVER_COGS:
                cog = self.bot.get_cog(cogName)
                await cog.initialize()
                
            self._print("init",'------', cog=self.COG_NAME)
            
        
        else:
            self.initialized = False
            self._print("init","load looped tasks", cog=self.COG_NAME)
            for server in self.bot.guilds:
                self.loadLoopRoutines(server)
            self._print("init",'------', cog=self.COG_NAME)
            self._print("init","load cogs", cog=self.COG_NAME)
            
            for cogName in self.SERVER_COGS:
                cog = self.bot.get_cog(cogName)
                await cog.init_on_error()
            self._print("init",'------', cog=self.COG_NAME)        
            self.initialized = True
        self._print("init",'Initialization complete', cog=self.COG_NAME)
        self._print("init",'------', cog=self.COG_NAME)
        
    @commands.Cog.listener()
    async def on_guild_join(self, server):
        '''Adds newly added servers to the SERVER_VARS dict and starts their looped tasks.'''
        
        self._print(server.id,  "NEW SERVER ARRIVED", cog=self.COG_NAME)
        
        #add server do global var dict
        self.SERVER_VARS[server.id] = self.ServerNode(server.id)
        
        # ad routines for new server
        self.loadLoopRoutines(server)
        
        self._print(server.id,  "NEW SERVER INITIALIZED", cog=self.COG_NAME)
    
    @commands.Cog.listener()
    async def on_guild_remove(self, server):
        '''Removes leaving servers from the SERVER_VARS dict and settings file.'''
        
        self._print(server.id,  "SERVER REMOVED", cog=self.COG_NAME)
        # remove server from global var dict
        
        self.SERVER_VARS.pop(server.id, None)
        
        # remove server from save file
        with open(self.SETTINGS_FILE, "r+") as read_file:
            data = json.load(read_file)
            
            if server.id in list(data):
                del data[server.id]
                
            read_file.seek(0)
            json.dump(data, read_file, indent=4)
            read_file.truncate()
            
            self.SETTINGS = data
            
        self._print(server.id,  "SAVEDATA CLEARED", cog=self.COG_NAME)

    @commands.Cog.listener()
    async def on_message(self, message):
        '''Gets called when messages are posted.
        
        Handles custom commands.
        '''
        
        if self.initialized and not message.guild == None:
            server = message.guild.id
            
            # ignore own messages
            if message.author == self.bot.user or message.author.bot:
                return
            
            # check if user is already in a command process
            if message.author in self.SERVER_VARS[server].cmdLockout:
                #await bot.delete_message(message)
                #await notify(message.channel, "{} bitte warte, bis der letzte Befehl zu Ende ausgeführt wurde.".format(message.author.mention), 7)
                return
            
            # ignore actual commands
            if self.is_command(message.content, server):
                return
            # custom command handling
            elif self.is_custom_command(message.content, server):
                cmdDict = self.get_setting(server, 'COMMANDS')
                await message.channel.send(cmdDict[message.content[1:]])
                return
            # custom dmcommand handling
            elif self.is_custom_dmcommand(message.content, server):
                cmdDict = self.get_setting(server, 'DM_COMMANDS')
                await message.author.send(cmdDict[message.content[1:]])
                # await message.delete()
                return
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        '''Called, when reactions are added.
        
        Handles setting of new reactions after performing the set command.
        '''
        
        if self.initialized:    
            server = reaction.message.guild.id
            
            # ignore own reactions
            if user == self.bot.user:
                return
                      
            # handling of change reactions command.
            if self.SERVER_VARS[server].msg1vs1:
                if reaction.message.id == self.SERVER_VARS[server].msg1vs1.id :
                    if await self.checkPermissions(user, reaction.message.channel):
                        if reaction.emoji in self.bot.emojis or isinstance(reaction.emoji, str):
                            self._print(server, "updating 1vs1 reaction", cog=self.COG_NAME)
                            
                            # handle custom emoji
                            if not isinstance(reaction.emoji, str):
                                emoji = reaction.emoji.name + ":" + str(reaction.emoji.id)
                            else:
                                emoji = reaction.emoji
                            
                            # update in settings
                            self.update_settings(server, 'REACTION_1VS1', emoji)
                            
                            await self.SERVER_VARS[server].msg1vs1.delete()
                            await self.notify(self.SERVER_VARS[server].msg1vs1.channel, "{} die 1vs1 Reaktion wurde aktualisiert. ".format(user.mention) + str(reaction.emoji))
                            channel = self.bot.get_channel(self.get_setting(server, 'MAINCHANNEL'))
                            
                            matchMaker = self.bot.get_cog("MatchMaking")
                            await matchMaker.postMessage(channel)
                            self.SERVER_VARS[server].msg1vs1 = False
                        else:
                            await self.notify(reaction.message.channel, "{} ich habe leider keinen Zugriff auf dieses Emoji.".format(user.mention))
                            await self.SERVER_VARS[server].msg1vs1.delete()
                            self.SERVER_VARS[server].msg1vs1 = False
                    else:
                        await asyncio.sleep(0.5)            
                        await reaction.message.remove_reaction(reaction.emoji, user)
            elif self.SERVER_VARS[server].msg2vs2:
                if reaction.message.id == self.SERVER_VARS[server].msg2vs2.id:
                    if await self.checkPermissions(user, reaction.message.channel):
                        if reaction.emoji in self.bot.emojis or isinstance(reaction.emoji, str):
                            self._print(server, "updating 2vs2 reaction", cog=self.COG_NAME)
                            
                            # handle custom emoji
                            if not isinstance(reaction.emoji, str):
                                emoji = reaction.emoji.name + ":" + str(reaction.emoji.id)
                            else:
                                emoji = reaction.emoji
                            
                            # update in settings
                            self.update_settings(server, 'REACTION_2VS2', emoji)
                            
                            await self.SERVER_VARS[server].msg2vs2.delete()
                            await self.notify(self.SERVER_VARS[server].msg2vs2.channel, "{} die 2vs2 Reaktion wurde aktualisiert. ".format(user.mention) + str(reaction.emoji))
                            channel = self.bot.get_channel(self.get_setting(server, 'MAINCHANNEL'))
                            
                            matchMaker = self.bot.get_cog("MatchMaking")
                            await matchMaker.postMessage(channel)
                            self.SERVER_VARS[server].msg2vs2 = False
                        else:
                            await self.notify(reaction.message.channel, "{} ich habe leider keinen Zugriff auf dieses Emoji.".format(user.mention))
                            await self.SERVER_VARS[server].msg2vs2.delete()
                            self.SERVER_VARS[server].msg2vs2 = False
                    else:
                        await asyncio.sleep(0.5)            
                        await reaction.message.remove_reaction(reaction.emoji, user)
    
    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        '''Custom error handler to log all errors in file.
        Otherwise internal Exceptions wont be logged.
        '''
        
        try:
            raise 
        except Exception as e:
            print(traceback.print_exc())
            self.bot.logger.exception("Uncaught exception[" + self.COG_NAME + "]: {0}".format(str(e)))
    
    @commands.Cog.listener() 
    async def on_command_error(self, ctx, exception):
        '''Custom command error handler to log all errors in file.
        Otherwise internal Exceptions wont be logged.
        '''
        
        try:
            raise exception
        except Exception as e:
            print(traceback.print_exc())
            self.bot.logger.exception("Uncaught exception[" + self.COG_NAME + "]: {0}".format(str(e)))
    
    #===============================================================================
    # Commands
    #===============================================================================
    
    @commands.command(name="set")
    async def _set(self, ctx, *args):
        '''Command to set the different Settings.
        view help command for more.
        
        :param ctx: context of command call
        '''
            
        user = ctx.message.author
        message = ctx.message
        server = message.guild.id
        
        
        repost = False
        cleanup = [message]
        
        
        if await self.checkPermissions(user, message.channel):
            error = ""
            self._print(server, str(user.name) + ":" + str(user.id) + " used command: set " + " ".join(args), cog=self.COG_NAME)
                    
            if len(args) > 0:
                
                
                
                
                if args[0] == 'prefix':
                    #===============================================================
                    # PREFIX handling
                    #===============================================================
                    
                    if len(args) == 2:
                        if len(args[1]) == 1:
                            
                            self.update_settings(server, 'PREFIX', args[1])
                            error = "{} Prefix updated. New prefix: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "\""
                        
                        else:
                            error = "{} The prefix has to be a single character. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set prefix !\""
                    else:
                        error = "{} Wrong number of arguments. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set prefix !\""
                
                
                
                
                elif args[0] == 'message' :
                    if len(args) == 1:
                        # no arguments given
                        error = "{} Missing argument. Possible arguments: content, timer, interval".format(user.mention) 
                    
                    
                    elif args[1] == 'content':
                        #===============================================================
                        # MESSAGE_CONTENT handling
                        #===============================================================
                        self.SERVER_VARS[server].cmdLockout.append(user)
                        
                        botPrompt = await message.channel.send("{} Your next message in this channel will be saved as the new main MatchMaking message.\n Reply with \"stop\" to abort.".format(user.mention))
                        
                        def check_1(m):
                            return m.author == user and m.channel == message.channel
                        
                        try:
                            newMessage = await self.bot.wait_for('message', timeout = 120, check=check_1)
                        except asyncio.TimeoutError:
                            newMessage = None
                        
                        cleanup.append(botPrompt)
                        
                        if newMessage:
                            cleanup.append(newMessage)
                        
                            # darf nicht mit prefix beginnen.
                            if not newMessage.content[0] == str(self.get_setting(server, 'PREFIX')):
                                if not newMessage.content == "stop":               
                                    # update settings
                                    self.update_settings(server, 'MESSAGE_CONTENT', newMessage.content)
                                    
                                    repost = True
                                    
                                    error = "{} Main message updated.".format(user.mention)
                                
                                else:
                                    error = "{} Process aborted, main message not updated.".format(user.mention)
                            else:
                                error = "{} The message cannot start with \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "\"."
                        else:
                            error = "{} Process aborted, request timed out.".format(user.mention)
                    
                    elif args[1] == 'timer':
                        #===============================================================
                        # MESSAGE_REPOST_TIME handling
                        #===============================================================
                        
                        if len(args) == 3:
                            
                            # check if number is valid
                            try: 
                                timeInSeconds = int(args[2])
                                self.update_settings(server, 'MESSAGE_REPOST_TIME', timeInSeconds)
                                
                                timeStr = str(datetime.timedelta(seconds=timeInSeconds))
                                                            
                                error = "{} Time interval updated. New main message will be posted every ".format(user.mention) + timeStr
                            
                            except ValueError:
                                error = "{} Time has to be in seconds. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set message timer 600\""
                        else:
                            error = "{} Wrong number of arguments. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set message timer 600\""
                    
                    
                    elif args[1] == 'interval':
                        #===============================================================
                        # MESSAGE_INTERVAL handling
                        #===============================================================
                        
                        if len(args) == 3:
                            
                            # check if number is valid
                            try: 
                                count = int(args[2])
                                self.update_settings(server, 'MESSAGE_INTERVAL', count)
                                
                                repost = True
                                
                                error = "{} Message interval updated. New main message will be posted every ".format(user.mention) + str(count) + " messages."
                            
                            except ValueError:
                                error = "{} Argument has to be a number. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set message interval 20\""
                        else:
                            error = "{} Wrong number of arguments. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set message interval 20\""
                    else:
                        error = "{} Wrong argument. Possible arguments: content, timer, interval".format(user.mention)
                    
                
                
                
                elif args[0] == 'reaction':
                    #===============================================================
                    # REACTION_XVSX handling
                    #===============================================================
                    
                    if len(args) == 1:
                        error = "{} Missing argument. Possible arguments: 1vs1, 2vs2".format(user.mention)
                         
                    elif args[1] == '1vs1':
                        react1vs1 = await message.channel.send("{} Please react with the 1vs1 Reaction of your choice.".format(user.mention))
                        self.SERVER_VARS[server].msg1vs1 = react1vs1
                        
                    elif args[1] == '2vs2':
                        react2vs2 = await message.channel.send("{} Please react with the 2vs2 Reaction of your choice.".format(user.mention))
                        self.SERVER_VARS[server].msg2vs2 = react2vs2
                        
                        # the rest of the implementation can be found in on_reaction_add
                    else:
                        error = "{} Wrong argument. Possible arguments: 1vs1, 2vs2".format(user.mention) 
                
                
                
                
                elif args[0] == 'role':
                    #===============================================================
                    # ROLE_XVSX handling
                    #===============================================================
                                    
                    if len(args) == 1:
                        error = "{} Missing argument. Possible arguments: 1vs1, 2vs2, timeout".format(user.mention)
                    elif len(args) == 2 and (args[1] == '1vs1' or args[1] == '2vs2'):
                        error = "{} Missing argument. Please input the name of a Role. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set role 1vs1 rolename\""
                         
                    elif args[1] == '1vs1':
                        
                        roleName = " ".join(args[2:])
                        
                        if not roleName == self.get_setting(message.guild.id, 'ROLE_2VS2'):
                                
                            role = get(user.guild.roles, name=roleName)
                        
                            if role:
                                # remove old role members
                                matchMaker = self.bot.get_cog("MatchMaking")
                                
                                for memberID in list(matchMaker.SERVER_VARS[server].singlesDict):
                                    
                                    member = self.bot.get_guild(server).get_member(memberID)
                                    role = get(member.guild.roles, name=str(self.get_setting(server, 'ROLE_1VS1')))
                                    
                                    if member and role:
                                        await member.remove_roles(role)
                                        self._print(server, "removed 1vs1 from " + str(member), cog=self.COG_NAME)
                                
                                self.update_settings(server, 'ROLE_1VS1', roleName)
                                
                                error = "{} Updated 1vs1 role: ".format(user.mention) + str(self.get_setting(server, 'ROLE_1VS1'))
                                
                            else:
                                error = "{} Role does not exist.".format(user.mention)
                        
                        else:
                            error = "{} 1vs1 and 2vs2 cannot have the same role.".format(user.mention)
                            
                    elif args[1] == '2vs2':
                        
                        roleName = " ".join(args[2:])
                        
                        if not roleName == self.get_setting(message.guild.id, 'ROLE_1VS1'):
                              
                            role = get(user.guild.roles, name=roleName)
                        
                            if role:
                                # remove old role members
                                matchMaker = self.bot.get_cog("MatchMaking")
                                for memberID in list(matchMaker.SERVER_VARS[server].doublesDict):
                                    
                                    member = self.bot.get_guild(server).get_member(memberID)
                                    role = get(member.guild.roles, name=str(self.get_setting(server, 'ROLE_2VS2')))
                                    
                                    if member and role:
                                        await member.remove_roles(role)
                                        self._print(server, "removed 2vs2 from " + str(member), cog=self.COG_NAME)
                                
                                self.update_settings(server, 'ROLE_2VS2', roleName)
                                
                                error = "{} Updated 2vs2 role: ".format(user.mention) + str(self.get_setting(server, 'ROLE_2VS2'))
                                
                            else:
                                error = "{} Role does not exist.".format(user.mention)
                        else:
                            error = "{} 1vs1 and 2vs2 cannot have the same role.".format(user.mention)
                        
                    elif args[1] == 'timeout':
                        if len(args) == 3 :
                            
                            # check if number is valid
                            try: 
                                timeInSeconds = int(args[2])
                                self.update_settings(server, 'ROLE_TIMEOUT', timeInSeconds)
                                
                                timeStr = str(datetime.timedelta(seconds=timeInSeconds))
                                
                                repost = True
                                
                                error = "{} Time Interval updated. Roles will be removed after: ".format(user.mention) + timeStr
                            
                            except ValueError:
                                error = "{} Time has to be in seconds. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set role timeout 600\""
                                            
                        else:
                            error = "{} Wrong arguments. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set role timeout 600\""
                    else:
                        error = "{} Wrong argument. Possible arguments 1vs1, 2vs2, timeout".format(user.mention)
                
                
                
                    
                elif args[0] == 'checkinterval':
                    
                    if len(args) == 1:
                        error = "{} Missing argument. Possible arguments: roles, message".format(user.mention)
                    elif not len(args) == 3:
                        error = "{} Wrong arguments. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set checkinterval roles 60\""
                        
                    elif args[1] == 'roles':
                        #===============================================================
                        # CHECK_INTERVAL_ROLES handling
                        #===============================================================
                        
                        # check if number is valid
                        try: 
                            timeInSeconds = int(args[2])
                            self.update_settings(server, 'CHECK_INTERVAL_ROLES', timeInSeconds)
                            
                            timeStr = str(datetime.timedelta(seconds=timeInSeconds))
                                                    
                            error = "{} Time interval updated. Roles will be checked every ".format(user.mention) + timeStr + "."
                        
                        except ValueError:
                            error = "{} Time has to be in seconds. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set checkinterval roles 60\""
                                       
                        
                    elif args[1] == 'message':
                        #===============================================================
                        # CHECK_INTERVAL_REPOST handling
                        #===============================================================
                        
                        # check if number is valid
                        try: 
                            timeInSeconds = int(args[2])
                            self.update_settings(server, 'CHECK_INTERVAL_REPOST', timeInSeconds)
                            
                            timeStr = str(datetime.timedelta(seconds=timeInSeconds))
                                                    
                            error = "{} Time interval updated. The bot will check every ".format(user.mention) + timeStr + " ,if enough time has passed to post a new message."
                        
                        except ValueError:
                            error = "{} Time has to be in seconds. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set checkinterval roles 60\""
                                
                    else:
                        error = "{} Wrong argument. Possible arguments: roles, message".format(user.mention) 
                    
                elif args[0] == 'command':
                    #===============================================================
                    # CUSTOM_COMMAND handling
                    #===============================================================
                    self.SERVER_VARS[server].cmdLockout.append(user)
                    
                    if len(args) == 2:
                        
                        command = str(args[1])
                        
                        if command not in self.SERVER_COMMANDS:
                        
                            botPrompt = await message.channel.send("{} Your next message in this channel will be used as the bot-reply to the command \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + command + "\".\nReply with \"stop\" to abort. \nReply with \"delete\" to remove an old command.")
                            
                            def check_2(m):
                                return m.author == user and m.channel == message.channel
                            
                            try:
                                newMessage = await self.bot.wait_for('message', timeout = 120, check=check_2)
                            except asyncio.TimeoutError:
                                newMessage = None
                            
                            cleanup.append(botPrompt)
                            
                            if newMessage:
                                cleanup.append(newMessage)
                            
                                # cannot start with prefix
                                if not newMessage.content[0] == str(self.get_setting(server, 'PREFIX')):
                                    if not newMessage.content == "stop":               
                                        # update settings
                                        self.update_settings(server, 'COMMANDS', newMessage.content, customCmd=command)
                                                                            
                                        error = "{} Command \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + command + "\" updated."
                                    
                                    else:
                                        error = "{} Command was not updated.".format(user.mention)
                                else:
                                    error = "{} Reply cannot start with \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "\"."
                            else:
                                error = "{} Request timed out.".format(user.mention)
                        else:
                            error = "{} This Command is already used by the bot.".format(user.mention)
                    else:
                        error = "{} Wrong arguments. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set command exampleCommand\""
                    
                
                elif args[0] == 'dmcommand':
                    #===============================================================
                    # CUSTOM_COMMAND_DM handling
                    #===============================================================
                    self.SERVER_VARS[server].cmdLockout.append(user)
                    
                    if len(args) == 2:
                        
                        command = str(args[1])
                        
                        if command not in self.SERVER_COMMANDS:
                        
                            botPrompt = await message.channel.send("{} Your next message in this channel will be used as the (direct message) bot-reply to the command \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + command + "\" Reply with \"stop\" to abort. \nReply with \"delete\" to remove an old command.")
                            
                            def check_3(m):
                                return m.author == user and m.channel == message.channel
                            
                            try:
                                newMessage = await self.bot.wait_for('message', timeout = 120, check=check_3)
                            except asyncio.TimeoutError:
                                newMessage = None
                            
                            cleanup.append(botPrompt)
                            
                            if newMessage:
                                cleanup.append(newMessage)
                            
                                # cannot start with prefix
                                if not newMessage.content[0] == str(self.get_setting(server, 'PREFIX')):
                                    if not newMessage.content == "stop":               
                                        # update settings
                                        self.update_settings(server, 'DM_COMMANDS', newMessage.content, customDmCmd=command)
                                                                            
                                        error = "{} Command \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + command + "\" updated."
                                    
                                    else:
                                        error = "{} Command was not updated.".format(user.mention)
                                else:
                                    error = "{} Reply cannot start with \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "\"."
                            else:
                                error = "{} Request timed out.".format(user.mention)
                        else:
                            error = "{} This Command is already used by the bot.".format(user.mention)
                    else:
                        error = "{} Wrong arguments. Example: \"".format(user.mention) + str(self.get_setting(server, 'PREFIX')) + "set dmcommand beispielBefehl\""
                    
                
                    
                else:
                    error = "{} Wrong argument. Possible arguments: prefix, message, reaction, role, checkinterval, command, dmcommand".format(user.mention)
            else:
                # TODO help here
                error = "{} Missing argument. Possible arguments:: prefix, message, reaction, role, checkinterval, command, dmcommand".format(user.mention)
            
            # notify error, if one occured
            if not error == "":
                await self.notify(message.channel, error, 5)    
        
        #cleanup
        if len(cleanup) > 1:
            await message.channel.delete_messages(cleanup)
        elif len(cleanup) == 1:
            await cleanup[0].delete()
        
        if user in self.SERVER_VARS[server].cmdLockout:
            self.SERVER_VARS[server].cmdLockout.remove(user)
        
        # only repost Message neccessary
        if repost:
            channel = self.bot.get_channel(self.get_setting(server, 'MAINCHANNEL'))
            matchMaking = self.bot.get_cog("MatchMaking")
            await matchMaking.postMessage(channel)
    
    @commands.command(name="get")
    async def _get(self, ctx, *args):
        '''Command to get current state of specific settings.
        
        :param ctx: context of command call
        '''
        
            
        user = ctx.message.author
        message = ctx.message
        server = message.guild.id
        
        
        cleanup = [message]
        
        if await self.checkPermissions(user, message.channel):
            
            self._print(server, str(user.name) + ":" + str(user.id) + " used command: get " + " ".join(args), cog=self.COG_NAME)
            
            returnStr = ""
            if len(args) > 0:
                
                
                if args[0] == 'prefix':
                    #===============================================================
                    # PREFIX handling
                    #===============================================================
                    
                    returnStr = "{} Das Prefix lautet: \n".format(user.mention) + str(self.get_setting(message.guild.id, 'PREFIX'))
                
                elif args[0] == 'message' :
                    
                    if not len(args) == 2:
                        
                        returnStr = "{} zu wenig Argumente. Mögliche Argumente: content, timer, interval".format(user.mention)
                        
                    elif args[1] == 'content':
                        #===============================================================
                        # MESSAGE_CONTENT handling
                        #===============================================================
                        
                        returnStr = "{} Die aktuelle Nachricht lautet: \n".format(user.mention) + str(self.get_setting(message.guild.id, 'MESSAGE_CONTENT'))
                        
                    elif args[1] == 'timer':
                        #===============================================================
                        # MESSAGE_REPOST_TIME handling
                        #===============================================================
                        
                        timeStr = str(datetime.timedelta(seconds=self.get_setting(message.guild.id, 'MESSAGE_REPOST_TIME')))
                        returnStr = "{} Die Nachricht wird automatisch erneut gepostet nach: \n".format(user.mention) + timeStr
                    
                    elif args[1] == 'interval':
                        #===============================================================
                        # MESSAGE_INTERVAL handling
                        #===============================================================
                        
                        returnStr = "{} Anzahl der Nachrichten, bis die Bot-Nachticht erneut gepostet wird: \n".format(user.mention) + str(self.get_setting(message.guild.id, 'MESSAGE_INTERVAL'))
                        
                    else:
                        returnStr = "{} fehlerhafte Argumente. Mögliche Argumente: content, timer, interval".format(user.mention)
                    
                
                
                
                elif args[0] == 'reaction':
                    #===============================================================
                    # REACTION_XVSX handling
                    #===============================================================
                    
                    if not len(args) == 2:
                        
                        returnStr = "{} zu wenig Argumente. Mögliche Argumente: 1vs1, 2vs2".format(user.mention)
                         
                    elif args[1] == '1vs1':
                        
                        returnStr = "{} Die aktuelle Reaktion für 1vs1: \n".format(user.mention) + str(self.get_setting(message.guild.id, 'REACTION_1VS1'))
                        
                    elif args[1] == '2vs2':
                        
                        returnStr = "{} Die aktuelle Reaktion für 2vs2: \n".format(user.mention) + str(self.get_setting(message.guild.id, 'REACTION_2VS2'))
                        
                    else:
                        returnStr = "{} fehlerhafte Argumente. Mögliche Argumente: 1vs1, 2vs2".format(user.mention)
                
                
                
                
                elif args[0] == 'role':
                    #===============================================================
                    # ROLE_XVSX handling
                    #===============================================================
                                    
                    if not len(args) == 2:
                        
                        returnStr = "{} zu wenig Argumente. Mögliche Argumente: 1vs1, 2vs2, timeout".format(user.mention)
                        
                    elif args[1] == '1vs1':
                        
                        returnStr = "{} Die aktuelle 1vs1 Rolle: \n".format(user.mention) + str(self.get_setting(message.guild.id, 'ROLE_1VS1'))
                        
                    elif args[1] == '2vs2':
                        
                        returnStr = "{} Die aktuelle 2vs2 Rolle: \n".format(user.mention) + str(self.get_setting(message.guild.id, 'ROLE_2VS2'))
                    
                    elif args[1] == 'timeout':
                        
                        timeStr = str(datetime.timedelta(seconds=self.get_setting(message.guild.id, 'ROLE_TIMEOUT')))
                        returnStr = "{} Die Rolle wird automatisch entfernt nach: \n".format(user.mention) + timeStr
                        
                    else:
                        
                        returnStr = "{} fehlerhafte Argumente. Mögliche Argumente: 1vs1, 2vs2, timeout".format(user.mention)
                
                
                
                    
                elif args[0] == 'checkinterval':
                    
                    if not len(args) == 2:
                        
                        returnStr = "{} zu wenig Argumente. Mögliche Argumente: roles, message".format(user.mention)
                        
                    elif args[1] == 'roles':
                        #===============================================================
                        # CHECK_INTERVAL_ROLES handling
                        #===============================================================
                        
                        timeStr = str(datetime.timedelta(seconds=self.get_setting(message.guild.id, 'CHECK_INTERVAL_ROLES')))
                        returnStr = "{} Zeitintervall, in dem die Rollen überprüft werden: \n".format(user.mention) + timeStr  
                        
                    elif args[1] == 'message':
                        #===============================================================
                        # CHECK_INTERVAL_REPOST handling
                        #===============================================================
                        
                        timeStr = str(datetime.timedelta(seconds=self.get_setting(message.guild.id, 'CHECK_INTERVAL_REPOST')))
                        returnStr = "{} Zeitintervall, in dem die Nachricht überprüft wird: \n".format(user.mention) + timeStr
                             
                    else:
                        
                        returnStr = "{} fehlerhafte Argumente. Mögliche Argumente: roles, message".format(user.mention)
                    
                    
                    
                else:
                    returnStr = "{} fehlerhafte Argumente. Mögliche Argumente: prefix, message, reaction, role, checkinterval".format(user.mention) 
            else:
                # TODO help here
                returnStr = "{} zu wenig Argumente. Mögliche Argumente: prefix, message, reaction, role, checkinterval".format(user.mention)
            
            # notify error, if one occured
            if not returnStr == "":
                await self.notify(message.channel, returnStr, 10)
        if len(cleanup) > 1:
            await message.channel.delete_messages(cleanup)
        elif len(cleanup) == 1:
            await cleanup[0].delete()
    
    @commands.command()
    async def reset(self, ctx):
        '''Command to reset all settings to default.
        Current custom commands will not be removed.
        
        :param ctx: context of command call
        '''
        
         
        user = ctx.message.author
        message = ctx.message
        server = message.guild.id
                
        if await self.checkPermissions(user, message.channel):
            self._print(server, str(user.name) + ":" + str(user.id) + " used command: reset", cog=self.COG_NAME)
            self._print(server, "resetting to default.", cog=self.COG_NAME) 
            
            oldMainChannel = self.bot.get_channel(self.get_setting(server, 'MAINCHANNEL'))
            saveCMD = False
            saveDmCMD = False
            
            # remove server from save file
            with open(self.SETTINGS_FILE, "r+") as read_file:
                data = json.load(read_file)
                
                if str(server) in list(data):
                    # keep commands saved
                    if 'COMMANDS' in list(data[str(server)]):
                        saveCMD = data[str(server)]['COMMANDS']
                    if 'DM_COMMANDS' in list(data[str(server)]):
                        print("yes")
                        saveDmCMD = data[str(server)]['DM_COMMANDS']
                    
                    del data[str(server)]
                    
                read_file.seek(0)
                json.dump(data, read_file, indent=4)
                read_file.truncate()
                
                self.SETTINGS = data
                
                if saveCMD:
                    self.update_settings(server, 'COMMANDS', saveCMD)
                if saveDmCMD:
                    self.update_settings(server, 'DM_COMMANDS', saveDmCMD)
            
            if oldMainChannel:
                # delete old messages
                self._print(server,'Purge old messages', cog=self.COG_NAME)
                await oldMainChannel.purge(limit=100, check=self.is_me)
                
            self.SERVER_VARS[server].activeMessage = False
            
            await self.notify(message.channel, "{} Einstellungen wurden zurückgesetzt. Bitte erneut den Hauptkanal und die 1vs1/2vs2 Rollen setzen.".format(user.mention), 7)
            
            
        await message.delete()
    
    @commands.command()
    async def settings(self, ctx):
        '''Command to send a direct message to the user containing all current settings.
        
        :param ctx: context of command call
        '''
        
         
        user = ctx.message.author
        message = ctx.message
        server = message.guild.id
         
        if await self.checkPermissions(user, message.channel):
            
            self._print(server, str(user.name) + ":" + str(user.id) + " used command: settings", cog=self.COG_NAME)
            
            MAINCHANNEL = self.get_setting(server, 'MAINCHANNEL') 
            PREFIX = str(self.get_setting(server, 'PREFIX'))
            MESSAGE_INTERVAL = self.get_setting(server, 'MESSAGE_INTERVAL')
            MESSAGE_CONTENT = self.get_setting(server, 'MESSAGE_CONTENT')
            MESSAGE_REPOST_TIME = self.get_setting(server, 'MESSAGE_REPOST_TIME')
            REACTION_1VS1 = self.get_setting(server, 'REACTION_1VS1')
            REACTION_2VS2 = self.get_setting(server, 'REACTION_2VS2')
            ROLE_1VS1 = str(self.get_setting(server, 'ROLE_1VS1'))
            ROLE_2VS2 = str(self.get_setting(server, 'ROLE_2VS2'))
            ROLE_TIMEOUT = self.get_setting(server, 'ROLE_TIMEOUT')
            CHECK_INTERVAL_ROLES = self.get_setting(server, 'CHECK_INTERVAL_ROLES')
            CHECK_INTERVAL_REPOST = self.get_setting(server, 'CHECK_INTERVAL_REPOST')
                
            embed = discord.Embed(title="AKTUELLE EINSTELLUNGEN[" + message.guild.name + "]:", description="Folgene einstellungen wurden vorgenommen:  ", color=0x00ff00)
            
            embed.add_field(name="MAINCHANNEL:    \n" + str(MAINCHANNEL), value="ID des Kanals, in dem der Bot genutzt wird.", inline=False)
            
            embed.add_field(name="PREFIX:    \n" + str(PREFIX), value="Prefix vor Befehlen.", inline=False)
            
            embed.add_field(name="MESSAGE_INTERVAL:    \n" + str(MESSAGE_INTERVAL), value="Anzahl der Nachrichten, nach der der Bot automatisch erneut postet.", inline=False)
            
            embed.add_field(name="MESSAGE_CONTENT: \n" + str(MESSAGE_CONTENT), value="Inhalt der Hauptnachricht.", inline=False)
            
            embed.add_field(name="MESSAGE_REPOST_TIME:    \n" + str(MESSAGE_REPOST_TIME) + " (" + str(datetime.timedelta(seconds=MESSAGE_REPOST_TIME)) + ")", value="Zeit, nach der der Bot automatisch erneut postet. (In Sekunden)", inline=False)
            
            embed2 = discord.Embed(color=0x00ff00)
            
            embed2.add_field(name="REACTION_1VS1:    \n" + str(REACTION_1VS1), value="Reaktionsemoji zum suchen eines 1vs1.", inline=False)
            
            embed2.add_field(name="REACTION_2VS2:    \n" + str(REACTION_2VS2), value="Reaktionsemoji zum suchen eines 2vs2.", inline=False)
            
            embed2.add_field(name="ROLE_1VS1:    \n" + str(ROLE_1VS1), value="Name der Rolle für 1vs1 Suchende.", inline=False)
            
            embed2.add_field(name="ROLE_2VS2:    \n" + str(ROLE_2VS2), value="Name der Rolle für 2vs2 Suchende.", inline=False)
            
            embed2.add_field(name="ROLE_TIMEOUT:    \n" + str(ROLE_TIMEOUT) + " (" + str(datetime.timedelta(seconds=ROLE_TIMEOUT)) + ")", value="Zeit, nach der die Rollen automatisch entfernt werden. (In Sekunden)", inline=False)
            
            embed2.add_field(name="CHECK_INTERVAL_ROLES:    \n" + str(CHECK_INTERVAL_ROLES) + " (" + str(datetime.timedelta(seconds=CHECK_INTERVAL_ROLES)) + ")", value="Zeitabstand, nach dem der Bot regelmäßig die Rollen auf Timeouts überprüft. (In Sekunden)", inline=False)
            
            embed2.add_field(name="CHECK_INTERVAL_REPOST:    \n" + str(CHECK_INTERVAL_REPOST) + " (" + str(datetime.timedelta(seconds=CHECK_INTERVAL_REPOST)) + ")", value="Zeitabstand, nach dem der Bot regelmäßig prüft, ob genügend Zeit vergangen ist, um eine neue Nachricht zu posten. (In Sekunden)", inline=False)
            
            await user.send(embed=embed)
            await user.send(embed=embed2)
            # await notify(message.channel, "{} noch nicht implementiert.".format(user.mention))
        await asyncio.sleep(5)
        await message.delete()
    
    @commands.command()
    async def help(self, ctx, *args):
        '''Command to send a direct message to the user containing all possible commands.
        
        :param ctx: context of command call
        '''
          
        user = ctx.message.author
        message = ctx.message
        server = message.guild.id
        
        if await self.checkPermissions(user, message.channel):
            
            self._print(server, str(user.name) + ":" + str(user.id) + " used command: help " + " ".join(args), cog=self.COG_NAME)
            
            prefix = str(self.get_setting(server, 'PREFIX'))
            
            if len(args) == 0:
            
                helpStr  =          "```" 
                helpStr +=          "ACHTUNG: \n"
                helpStr +=          " \n"
                helpStr +=          "Bevor der Bot funktioniert müssen folgende Befehle ausgeführt werden: \n"
                helpStr +=          " \n"
                helpStr += "   " + prefix + "set role 1vs1 <value>    Setzt Rolle der 1vs1 Suchenden. <value> als Rollennamen.\n"
                helpStr += "   " + prefix + "set role 2vs2 <value>    Setzt Rolle der 2vs2 Suchenden. <value> als Rollennamen.\n"
                helpStr += "   " + prefix + "mainChannel   Setzt den aktuellen Kanal als Hauptkanal, in dem der Bot aktiv ist.\n"
                helpStr +=          " \n"
                helpStr +=          "Befehle: \n"
                helpStr +=          " \n"
                helpStr += prefix + "1vs1          Gibt die Rolle 1vs1 und benachrichtigt alle mit dieser Rolle.\n"
                helpStr += prefix + "2vs2          Gibt die Rolle 2vs2 und benachrichtigt alle mit dieser Rolle.\n"
                helpStr += prefix + "roll          Würfelt eine Zahl zwischen 0 und 9.\n"
                helpStr += prefix + "mainChannel   Setzt den Kanal als Hauptkanal, in dem der Bot aktiv ist.\n"
                helpStr += prefix + "set           Setzt die einzelnen Einstellungen. Mögliche Optionen: " + prefix + "help set\n" 
                helpStr += prefix + "get           Fragt den aktuellen Wert der Einstellungen ab. Unteroptionen analog zu set.\n"
                helpStr += prefix + "reset         Setzt alle Einstellungen auf den Standartwert zurück.\n"
                helpStr += prefix + "settings      Schickt eine private Nachricht an den Nutzer mit den Aktuellen Einstellungen.\n"
                helpStr += prefix + "commands      Schickt eine private Nachricht an den Nutzer mit allen Custom Befehlen.\n"
                helpStr += prefix + "post          Postet die Hauptnachricht erneut.\n"
                helpStr += prefix + "version       Postet die Version des Bots.\n"
                helpStr +=          "```"
                
                await user.send(helpStr)
                
                
            elif len(args) == 1 and args[0] == 'set':
                
                helpStr  =          "```" 
                helpStr +=          "Set Befehl Hilfe: \n"
                helpStr +=          " \n"
                helpStr += prefix + "set prefix <value>                Setzt das Prefix. <value> muss einzelnes Zeichen sein.\n"
                helpStr += prefix + "set message content               Ändert die Hauptnachricht.\n"
                helpStr += prefix + "set message timer <value>         Setzt die Zeit, nach der erneut gepostet wird. <value>\n"
                helpStr +=          "                                   in Sekunden.\n"
                helpStr += prefix + "set message interval <value>      Setzt die Zahl der Nachrichten, nach der erneut gepostet \n"
                helpStr +=          "                                   wird. <value> als Zahl. \n"
                helpStr += prefix + "set reaction 1vs1                 Ändert die 1vs1 Reaktion.\n"
                helpStr += prefix + "set reaction 2vs2                 Ändert die 1vs1 Reaktion.\n"
                helpStr += prefix + "set role 1vs1 <value>             Setzt Rolle der 1vs1 Suchenden. <value> als Rollennamen.\n"
                helpStr += prefix + "set role 2vs2 <value>             Setzt Rolle der 2vs2 Suchenden. <value> als Rollennamen.\n"
                helpStr += prefix + "set role timeout <value>          Setzt die Zeit, nach der die Rollen aberkannt werden. \n"
                helpStr +=          "                                   <value> in Sekunden. \n"
                helpStr += prefix + "set command <value>               Fügt den Befehl <value> hinzu, bearbeitet oder löscht ihn.\n"
                helpStr +=          "                                   Die Antwort des Befehls wird im gleichen Kanal gesendet.\n"
                helpStr += prefix + "set dmcommand <value>             Fügt den Befehl <value> hinzu, bearbeitet oder löscht ihn.\n"
                helpStr +=          "                                   Die Antwort des Befehls wird als Private Nachricht gesendet.\n"
                helpStr +=          " \n"
                helpStr +=          "v-----besser auf default lassen-----v \n"
                helpStr += prefix + "set checkinterval roles <value>   Setzt das Intervall, in dem die Rollen überprüft werden.\n"
                helpStr +=          "                                   <value> in Sekunden\n"
                helpStr += prefix + "set checkinterval message <value> Setzt das Intervall, in dem die Message überprüft wird.\n"
                helpStr +=          "                                   <value> in Sekunden\n"
                helpStr +=          "```"
                
                await user.send(helpStr)
            
        await message.delete()
    
    @commands.command()
    async def version(self, ctx):
        '''Command to get current version.
        
        :param ctx: context of command call
        '''
        
        user = ctx.message.author
        message = ctx.message
        server = ctx.message.guild.id
        
        if await self.checkPermissions(user, message.channel):
            
            self._print(server, str(user.name) + ":" + str(user.id) + " used command: version ", cog=self.COG_NAME)
            await self.notify(message.channel, "Aktuell genutzte Version: " + self.VERSION, 5) 
        
        await message.delete()
    
    @commands.command()
    async def restart(self, ctx):
        '''Command to restart the bot.
        Only Creator has permissions for this as it affects all connected servers.
        
        :param ctx: context of command call
        '''
        
        user = ctx.message.author
        message = ctx.message
        
        if await self.checkPermissions(user, message.channel, creator=True):
            await message.delete()
            #bot.loop.close()
            #await bot.logout()
            await self.bot.close()
        else:    
            await message.delete()
    
    @commands.command()
    async def reloadSettings(self, ctx):
        '''Command to reload the settings file.
        Only Creator has permissions for this.
        
        :param ctx: context of command call
        '''
        
        user = ctx.message.author
        message = ctx.message
        
        if await self.checkPermissions(user, message.channel, creator=True):
            self.init_settings()
            await message.delete()
        else:    
            await message.delete()
    
    @commands.command()
    async def debug(self, ctx):
        '''Executes debug code.
        
        :param ctx: context of command call
        '''
        
        user = ctx.message.author
        message = ctx.message
        
        if await self.checkPermissions(user, message.channel, creator=True):
            print("DEBUG")
            await message.delete()

    @commands.command()
    async def commands(self, ctx, *args):
        '''Command to send a direct message to the user containing all custom commands.
        
        :param ctx: context of command call
        '''
        
        user = ctx.message.author
        message = ctx.message
        server = message.guild.id
         
        if await self.checkPermissions(user, message.channel):
            
            self._print(server, str(user.name) + ":" + str(user.id) + " used command: commands", cog=self.COG_NAME)
            prefix = str(self.get_setting(server, 'PREFIX'))
            cmdDict = self.get_setting(server, 'COMMANDS')
            dmCmdDict = self.get_setting(server, 'DM_COMMANDS')
            
            
            if len(args) == 0:
                
                
                
                helpStr  =          "```" 
                helpStr +=          "[" + str(message.guild.name) + "] \n" 
                helpStr +=          "Liste aller Custom-Befehle, die im selben Kanal antworten: \n"
                helpStr +=          " \n"
                
                for command in list(cmdDict):
                    helpStr += "   " + prefix + str(command) + " \n"
                
                helpStr +=          " \n"
                helpStr +=          "Custom-Befehle, die als Antwort Private Nachrichten senden: \n"
                helpStr +=          " \n"
                
                for command in list(dmCmdDict):
                    helpStr += "   " + prefix + str(command) + " \n"
                
                helpStr +=          " \n"
                helpStr +=          "Um mehr Informationen zu einem Befehl zu erhalten, einfach \n"
                helpStr += "   " + prefix + "commands <name of command> \n"
                helpStr +=          "ohne das Prefix des gewünschten Befehls eingeben. \n"
                helpStr +=          "```" 
                
                
                await user.send(helpStr)
                
                
            elif len(args) == 1:
                
                command = args[0]
                
                if command in list(cmdDict):
                    
                    helpStr =          "```Befehl " + prefix +command + ": ```"
                    helpStr +=          cmdDict[command]
                    helpStr +=          " ```Ende des Befehls. ```\n"
                    await user.send(helpStr)
                
                elif command in list(dmCmdDict):
                    
                    helpStr =          "```Befehl " + prefix +command + ": ```"
                    helpStr +=          dmCmdDict[command]
                    helpStr +=          " ```Ende des Befehls. ```\n"
                    await user.send(helpStr)
                    
                else:
                    await self.notify(message.channel, "{} dieser Befehl existiert nicht.".format(user.mention))
            else:
                await self.notify(message.channel, "{} dieser Befehl existiert nicht.".format(user.mention))
        await message.delete()
    
    
def setup(bot):
    bot.add_cog(Controller(bot))
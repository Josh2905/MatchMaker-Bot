'''
Created on 25.02.2019

@author: Joshua Esselmann
@version: 1.1.2
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
from cgi import maxlen


####################################################################################################
##DEFAULTS##
####################################################################################################
VERSION = "1.1.2"

AUTHOR_ID = 90043934247501824
SETTINGS_FILE = 'settings.json'
TOKEN_FILE = 'token.txt'

MAINCHANNEL = ''                  # right click on channel and select "copy ID"
ACTIVE_CHANNELS = {}
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

#===============================================================================
# global declarations
#===============================================================================

# Logger
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
#handler = logging.FileHandler(filename=logFileName, encoding='utf-8', mode='w')
handler = logging.handlers.TimedRotatingFileHandler("SLBot.log",'midnight', 1, 5, 'utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# dynamic prefixes
def get_prefix(bot, message):
    '''This method enables the use of custom Prefixes set by the user.'''
    serverid = str(message.guild.id)
    with open(SETTINGS_FILE) as f:
        data = json.load(f)
    
    if serverid in list(data) and 'PREFIX' in list(data[serverid]):
        prefix = data[serverid]['PREFIX']
    else:
        prefix = data['DEFAULTS']['PREFIX']
    
    return prefix

bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')
class serverNode():
    '''This class is used to store variables for each connected Server.'''
    
    def __init__(self, _id):
        self.id = _id
        self.msgCounter = 0
        self.activeMessage = False
        self.singlesDict = {}
        self.doublesDict = {}
        self.searchMessageSinglesDict = {}
        self.searchMessageDoublesDict = {}
        self.msgTimer = datetime.datetime.utcnow()
        
        #last 10 messages as a stack
        self.lastMsgStack = deque(maxlen=10)
        
        #bools to keep track of running coroutines
        self.commandTimeout = False
        self.checkTimeout = False
        self.repostMessage = False
        
        
        self.cmdLockout = []
        
        # active commands
        self.msg1vs1 = False
        self.msg2vs2 = False

SERVER_VARS = {}
SETTINGS = {}
SERVER_COMMANDS = ["1vs1","2vs2","mainChannel","set","get","reset", "settings", "post", "commands", "help", "version", "restart"]
initialized = False

#===============================================================================
# helper Methods
#===============================================================================

def _print(server, message, log=True):
    '''A custom print command, that adds additional formatting to the output and also logs it with a logger.
    
    :param server: Server ID performing the action to be logged.
    :param message: String that will be logged.
    :param log: Decides, if message will be logged in a file or just the console.
    '''
    logStr = "<" + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + ">"
    serverObj = bot.get_guild(server)
    if serverObj:
        d = "[" + str(serverObj.name) + ":" + str(server) +"] "
        logStr += d
    else:
        d = "[" + str(server) + "]  "
        logStr += d
    logStr += str(message)
    print(logStr)
    if log:
        logger.info(str("APPLICATION" + d + str(message)))
    
def init_settings():
    '''Loads saved settings from json file and creates a 
    file with default values if it doesnt already exist.
    '''
    
    global PREFIX, MAINCHANNEL, ACTIVE_CHANNELS, MESSAGE_CONTENT, MESSAGE_INTERVAL, MESSAGE_REPOST_TIME, REACTION_1VS1, REACTION_2VS2
    global ROLE_1VS1, ROLE_2VS2, ROLE_TIMEOUT, CHECK_INTERVAL_ROLES, CHECK_INTERVAL_REPOST, SETTINGS
    
    #check if config file exists
    if not os.path.exists(SETTINGS_FILE):
         
        _print("main","Creating settings file, using default values")
                
        data = {
            "DEFAULTS": {
                'PREFIX': PREFIX,
                'MAINCHANNEL': MAINCHANNEL,
                'ACTIVE_CHANNELS': ACTIVE_CHANNELS,
                'MESSAGE_CONTENT': MESSAGE_CONTENT,
                'MESSAGE_INTERVAL' : MESSAGE_INTERVAL,
                'MESSAGE_REPOST_TIME': MESSAGE_REPOST_TIME,
                'REACTION_1VS1': REACTION_1VS1,
                'REACTION_2VS2': REACTION_2VS2,
                'ROLE_1VS1': ROLE_1VS1,
                'ROLE_2VS2': ROLE_2VS2,
                'ROLE_TIMEOUT': ROLE_TIMEOUT,
                'CHECK_INTERVAL_ROLES': CHECK_INTERVAL_ROLES,
                'CHECK_INTERVAL_REPOST': CHECK_INTERVAL_REPOST,
                'COMMANDS': COMMANDS,
                'DM_COMMANDS': DM_COMMANDS,
            }
        }
        with open(SETTINGS_FILE, 'w') as configfile:
            json.dump(data, configfile, indent=4)
        
        SETTINGS = data
        _print("main","Settings created successfully")
    else:
        _print("main","Load settings from settings.json")
        with open(SETTINGS_FILE, "r") as read_file:
            data = json.load(read_file)
                          
            SETTINGS = data
        _print("main","Settings loaded")
        
def update_settings(_server, key, value, customCmd=False, customDmCmd=False):
    '''Updates settings file with new Values, loads new settings into the global settings dict.
    
    :param server: Server ID 
    :param key: Key value of settings file
    :param value: Corresponding value 
    :param customCmd: if it is a custom command or not.
    '''
    with open(SETTINGS_FILE, "r+") as read_file:
        data = json.load(read_file)
        
        server = str(_server)
        
        # add new setting to data, if missing
        if server not in list(data):
            newEntry = {}
            data[server] = newEntry
        
        #check for active channel changes
        if key == "ACTIVE_CHANNELS":
            if 'ACTIVE_CHANNELS' not in list(data[server]):
                newEntry = {}
                data[server]['ACTIVE_CHANNELS'] = newEntry
            
            if value in data[server]['ACTIVE_CHANNELS']:
                data[server]['ACTIVE_CHANNELS'].pop(value, None)
            else:   
                data[server]['ACTIVE_CHANNELS'].append(value)
            
        
        #check if new command was added
        elif customCmd:
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
        
        global SETTINGS
        SETTINGS = data
        _print(_server, "Settings updated: " + str(key) + " = " + str(value))
                   
def get_setting(server, key):
    ''' Gets setting value from global settings dict.
    
    :param server: Server ID
    :param key: Key of Setting
    '''
    value = None
    global SETTINGS
    if str(server) in list(SETTINGS) and key in list(SETTINGS[str(server)]):
        value = SETTINGS[str(server)][key]
    else:
        value = SETTINGS['DEFAULTS'][key]
    
    try:
        value = int(value)
    except:
        pass
    
    return value
    
def is_setup(server):
    '''Return, wether all neccessary settings are set for the bot to be fully functional.
    
    :param server: Server ID
    '''
    global SETTINGS
    
    if str(server) in list(SETTINGS) and 'MAINCHANNEL' in list(SETTINGS[str(server)]) and 'ROLE_1VS1' in list(SETTINGS[str(server)]) and 'ROLE_2VS2' in list(SETTINGS[str(server)]):
        return True
    else:
        return False

def is_command(cmd, server):
    '''Return, if a command with this name exists.
    
    :param cmd: Command name
    :param server: Server ID
    '''
    if len(cmd) > 1 and cmd[0] == str(get_setting(server, 'PREFIX')):
            
        command = cmd[1:]
        
        mainCommand = command.split(" ", 1)[0]
        
        if mainCommand in SERVER_COMMANDS:
            return True
    return False

def is_custom_command(cmd, server):
    '''Return, if a custom command with this name exists.
    
    :param cmd: Command name
    :param server: Server ID
    '''
    if len(cmd) > 1 and cmd[0] == str(get_setting(server, 'PREFIX')):
            
        command = cmd[1:]
        
        cmdDict = get_setting(server, 'COMMANDS')
        
        if command in list(cmdDict):
            return True
    return False

def is_custom_dmcommand(cmd, server):
    '''Return, if a custom dmcommand with this name exists.
    
    :param cmd: Command name
    :param server: Server ID
    '''
    if len(cmd) > 1 and cmd[0] == str(get_setting(server, 'PREFIX')):
            
        command = cmd[1:]
        
        cmdDict = get_setting(server, 'DM_COMMANDS')
        
        if command in list(cmdDict):
            return True
    return False

def get_server_vars():
    '''Acces to SERVER_VARS for Cogs.'''
    return SERVER_VARS

def set_server_vars(server, key, value):
    '''Acces to SERVER_VARS for Cogs.'''
    SERVER_VARS[server].key = value

async def notify(channel, message, timeout=3):
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

async def notifySearch(channel, user, role):
    '''Notify a channel that someone is looking for a match.
    
    :param channel: Channel to be notified
    :param user: User in search of a match
    :param role: Role that is searched for
    '''
    
    global SERVER_VARS
    
    server = channel.guild.id
    
    role1vs1 = get(channel.guild.roles, name=str(get_setting(server, 'ROLE_1VS1')))
    role2vs2 = get(channel.guild.roles, name=str(get_setting(server, 'ROLE_2VS2')))
        
    if role == role1vs1:
        alert = "sucht nach einem 1vs1 Match! {}".format(role.mention)
        msg = await channel.send(user.mention + " " + alert)
        # await msg.add_reaction(REACTION_CANCEL)
        SERVER_VARS[server].searchMessageSinglesDict[user.id] = (channel.id, msg.id)
    
    elif role == role2vs2:
        alert = "sucht nach einem 2vs2 Match! {}".format(role.mention)
        msg = await channel.send(user.mention + " " + alert)
        # await msg.add_reaction(REACTION_CANCEL)
        SERVER_VARS[server].searchMessageDoublesDict[user.id] = (channel.id, msg.id)

async def singles(user, role, message):
    '''This method adds/removes a role from a discord servber member, informs him of that fact, removes the message together with its own 
    answer automatically after a few seconds.
     
    :param user: The member to be roled
    :param role: The role to be granted/removed (has to be 1vs1)
    :param message: The context of the original message
    '''
    
    server = message.guild.id
    
    if role:
        
        if role in user.roles:
            # remove role from user
            try:
                await user.remove_roles(role)
            except AttributeError:
                pass
            await notify(message.channel, "{} du hast nicht mehr die Rolle ".format(user.mention) + str(get_setting(server, 'ROLE_1VS1')) + ".", timeout=5)
            _print(server, "removed 1vs1 role from " + str(user.name))
        else:
            # grant user role
            await user.add_roles(role)
            await notifySearch(message.channel, user, role)
            # await notify(message.channel, "{0} du hast nun die Rolle ".format(user.mention) + str(get_setting(server, 'ROLE_1VS1')) + ".")
            _print(server, "applied 1vs1 role to " + str(user.name))
    else:
        await notify(message.channel, "{0} diese Rolle existiert nicht mehr. Bitte erneut setzen. (!help)".format(user.mention))
    
async def doubles(user, role, message):
    '''This method adds/removes a role from a discord servber member, informs him of that fact, removes the message together with its own 
    answer automatically after a few seconds. 
    
    :param user: The member to be roled
    :param role: The role to be granted/removed (has to be 2vs2)
    :param message: The context of the original message.
    '''
        
    server = message.guild.id
    
    if role:
        
        if role in user.roles:
            # remove role from user
            try:
                await user.remove_roles(role)
            except AttributeError:
                pass
            await notify(message.channel, "{} du hast nicht mehr die Rolle ".format(user.mention) + str(get_setting(server, 'ROLE_2VS2')) + ".", timeout=5)
            _print(server, "removed 2vs2 role from " + str(user.name))
        else:
            # grant user role
            await user.add_roles(role)
            await notifySearch(message.channel, user, role)
            # await notify(message.channel, "{} du hast nun die Rolle ".format(user.mention) + str(get_setting(server, 'ROLE_2VS2')) + ".")
            _print(server, "applied 2vs2 role to " + str(user.name))
    else:
        await notify(message.channel, "{0} diese Rolle existiert nicht mehr. Bitte erneut setzen. (!help)".format(user.mention))

async def postMessage(channel):
    '''Posts the main matchmaking message to the specified channel.
    removes the old message in the process. Returns new Message.
    
    :param channel: Channel where message will be posted.
    '''
    server = channel.guild.id
    
    if channel and is_setup(server):
        
        #remove old message
        if SERVER_VARS[server].activeMessage:
            await SERVER_VARS[server].activeMessage.delete()
              
        # send message
        SERVER_VARS[server].msgTimer = datetime.datetime.utcnow()
        SERVER_VARS[server].msgCounter = 0
        
        msg = await channel.send(get_setting(server, 'MESSAGE_CONTENT'))
        SERVER_VARS[server].activeMessage = msg
        
        #add reactions
        r1v1 = get(bot.emojis, name = get_setting(server, 'REACTION_1VS1'))
        if r1v1 == None:
            r1v1 = get_setting(server, 'REACTION_1VS1')
        
        
        r2v2 = get(bot.emojis, name = get_setting(server, 'REACTION_2VS2'))
        if r2v2 == None:
            r2v2 = get_setting(server, 'REACTION_2VS2')
        
        await msg.add_reaction(r1v1)
        await msg.add_reaction(r2v2)
        _print(server, "posting main message")
        
        return msg
        
    else:
        _print(server, "could not post message: server not fully set up")
        
        return None

async def checkPermissions(user, channel, creator=False):
    '''Returns, wether the user has permission to use the bots advanced features.
    
    :param user: User to be checked
    :param channel: channel the answer will be posted to
    :param creator: True, if only the creator has access
    '''
    if user.id == AUTHOR_ID or (not creator and user.guild_permissions.administrator):
        return True
    else:
        msg = await channel.send("{} du hast keine Rechte für diesen Befehl.".format(user.mention))
        await asyncio.sleep(3)
        await msg.delete()
        _print(channel.guild.id, str(user.name) + ":" + str(user.id) + " didnt have permissions.")
        return False
        
def is_me(m):
    '''Checks if bot is the author of a message.
    
    :param m: message to be checked.a
    '''
    return m.author == bot.user
    # block folding shit
    if True:
        pass

#===============================================================================
# looped routines    
#===============================================================================

async def commandTimeout(server):
    '''Periodically checks for role emoji change requests and lets them time out if unanswered.
    
    :param server: Server ID
    '''
    
    await bot.wait_until_ready()
    while not bot.is_closed():
        if initialized and (not get_setting(server, 'MAINCHANNEL') == get_setting('DEFAULTS', 'MAINCHANNEL')):
            
            global SERVER_VARS
            # change reaction command
            if SERVER_VARS[server].msg1vs1:
                difference = datetime.datetime.utcnow() - SERVER_VARS[server].msg1vs1.created_at
                _print(server, difference)
                if difference.total_seconds() > 60:
                    _print(server, "1v1 reaction change timed out")
                    await SERVER_VARS[server].msg1vs1.delete()
                    SERVER_VARS[server].msg1vs1 = False
            if SERVER_VARS[server].msg2vs2:
                difference = datetime.datetime.utcnow() - SERVER_VARS[server].msg2vs2.created_at
                if difference.total_seconds() > 60:
                    _print(server, "2v2 reaction change timed out")
                    await SERVER_VARS[server].msg2vs2.delete()
                    SERVER_VARS[server].msg2vs2 = False
            
        await asyncio.sleep(1000)
            
async def checkTimeout(server):
    '''Periodically checks for role timeouts and removes them if enough time has passed.
    
    :param server: Server ID
    '''
    
    await bot.wait_until_ready()
    while not bot.is_closed():
        
        global SERVER_VARS
        
        if initialized and is_setup(server) and (not get_setting(server, 'MAINCHANNEL') == get_setting('DEFAULTS', 'MAINCHANNEL')):
            if len(list(SERVER_VARS[server].singlesDict)) + len(list(SERVER_VARS[server].doublesDict)) > 0:
                _print(server, "checking for role timeouts:", log=False)
                
                srvr = bot.get_guild(server)
                
                for member in list(SERVER_VARS[server].singlesDict):
                    difference = datetime.datetime.utcnow() - SERVER_VARS[server].singlesDict[member]
                    difference -= datetime.timedelta(microseconds=difference.microseconds)
                    user = get(srvr.members, id=member)
                    _print(server, "| " + str(user) + " 1vs1 (" + str(difference) + "/" + str(str(datetime.timedelta(seconds=get_setting(server, 'ROLE_TIMEOUT')))) + ")", log=False)
                    if difference.total_seconds() > get_setting(server, 'ROLE_TIMEOUT'):
                        
                        role = get(srvr.roles, name=str(get_setting(server, 'ROLE_1VS1')))
                        
                        try:
                            await user.remove_roles(role)
                        except AttributeError:
                            pass
                        await asyncio.sleep(1)  #needed for no weird behaviour
                        _print(server, "timeout: removed 1vs1 from " + str(user))
                
                for member in list(SERVER_VARS[server].doublesDict):
                    difference = datetime.datetime.utcnow() - SERVER_VARS[server].doublesDict[member]
                    difference -= datetime.timedelta(microseconds=difference.microseconds)
                    user = get(srvr.members, id=member)
                    _print(server, str(user) + " 2vs2 (" + str(difference) + "/" + str(str(datetime.timedelta(seconds=get_setting(server, 'ROLE_TIMEOUT')))) + ")", log=False)
                    if difference.total_seconds() > get_setting(server, 'ROLE_TIMEOUT'):
                        
                        role = get(srvr.roles, name=str(get_setting(server, 'ROLE_2VS2')))
                        
                        try:
                            await user.remove_roles(role)
                        except AttributeError:
                            pass
                        await asyncio.sleep(1)
                        _print(server, "timeout: removed 2vs2 from " + str(user))
                      
        await asyncio.sleep(get_setting(server, 'CHECK_INTERVAL_ROLES')) #seconds

async def repostMessage(server):
    '''Periodically checks for the repost timeout of the main message and reposts it if enough time has passed.
    
    '''
    
    await bot.wait_until_ready()
    while not bot.is_closed():
        
        global SERVER_VARS
        
        if len(SERVER_VARS[server].lastMsgStack) > 0 and initialized and is_setup(server) and SERVER_VARS[server].activeMessage and (not get_setting(server, 'MAINCHANNEL') == get_setting('DEFAULTS', 'MAINCHANNEL')):
            
            timeDifference = datetime.datetime.utcnow() - SERVER_VARS[server].msgTimer
            timeLimit = get_setting(server, 'MESSAGE_REPOST_TIME')
                          
            if not (SERVER_VARS[server].lastMsgStack[-1] == SERVER_VARS[server].activeMessage.id):
                _print(server, "checking for message repost timeout (" + str(round(timeDifference.total_seconds(), 2)) + "/" + str(round(timeLimit, 2)) + ")", log=False)
            else:
                SERVER_VARS[server].msgTimer = datetime.datetime.utcnow()
            
            
            if timeDifference.total_seconds() > timeLimit:          
            
                channel = bot.get_channel(get_setting(server, 'MAINCHANNEL'))
                
                lastMsg = None
                
                try:
                    lastMsg = await channel.fetch_message(SERVER_VARS[server].lastMsgStack[-1])
                except IndexError:
                    pass
                except Exception as e:
                    print(traceback.print_exc())
                    logger.exception("Uncaught exception: {0}".format(str(e)))
                
                if lastMsg is not None:
                                        
                    if (not lastMsg.id == SERVER_VARS[server].activeMessage.id) and (not is_command(lastMsg.content, server)) and (not is_custom_command(lastMsg.content, server)):
                        
                        if is_me(lastMsg):
                            differenceToLastMsg = lastMsg.created_at - SERVER_VARS[server].msgTimer #timezone correction
                            # if last msg was posted by bot, it takes at least 7 minutes to have discord display them as seperate messages.
                            timeLimit = 430 + differenceToLastMsg.total_seconds()
                            _print(server,"prolonging time limit to seperate messages (" + str(round(timeDifference.total_seconds(), 2)) + "/" + str(round(timeLimit, 2)) + ")", log=False)
                        
                        if timeDifference.total_seconds() > timeLimit:
                            _print(server, "timeout: Reposting Message")
                            await postMessage(channel)
                    
                    else:
                        SERVER_VARS[server].msgTimer = datetime.datetime.utcnow()
                
        await asyncio.sleep(get_setting(server, 'CHECK_INTERVAL_REPOST'))
    
def loadLoopRoutines(server):    
    '''Loads Eventloop tasks for a server.
    
    :param server: Server
    '''
    global SERVER_VARS
    
    def callback_checkTimeout(serverID, task):
        SERVER_VARS[serverID].checkTimeout = False
        _print(server.id, "checkTimeout coro stopped \n!\n!\n!")
    def callback_repostMessage(serverID, task):
        SERVER_VARS[serverID].repostMessage = False
        _print(server.id, "repostMessage coro stopped \n!\n!\n!")
    def callback_commandTimeout(serverID, task):
        SERVER_VARS[serverID].commandTimeout = False
        _print(server.id, "commandTimeout coro stopped \n!\n!\n!")
    
    # add looped tasks to bot.
    if not SERVER_VARS[server.id].checkTimeout:
        future1 = bot.loop.create_task(checkTimeout(server.id))
        future1.add_done_callback(partial(callback_checkTimeout, server.id))
        SERVER_VARS[server.id].checkTimeout = True
        _print(server.id, "checkTimeout coro created")
    
    if not SERVER_VARS[server.id].repostMessage:
        future2 = bot.loop.create_task(repostMessage(server.id))
        future2.add_done_callback(partial(callback_repostMessage, server.id))
        SERVER_VARS[server.id].repostMessage = True
        _print(server.id, "repostMessage coro created")
        
    if not SERVER_VARS[server.id].commandTimeout:
        future3 = bot.loop.create_task(commandTimeout(server.id))
        future3.add_done_callback(partial(callback_commandTimeout, server.id))
        SERVER_VARS[server.id].commandTimeout = True
        _print(server.id, "commandTimeout coro created")
    
    if True:
        pass
        
#===============================================================================
# events
#===============================================================================


@bot.event
async def on_ready():
    '''Executed at the startup of the bot.
    Creates initial state, adds old roles to the tracker dicts and posts main message.
    '''
    global initialized
    if not initialized:
        _print("main", '------')
        _print("main", 'Logged in as')
        _print("main", bot.user.name)
        _print("main", bot.user.id)
        _print("main", '------')
        
        init_settings()
        
        _print("main",'------')
        
        _print("main",'initialize server variables')
        global SERVER_VARS
        for server in bot.guilds:
            SERVER_VARS[server.id] = serverNode(server.id)
        
        _print("main",'------')
        # remove all remaining matchmaking roles on startup
        _print("main",'init servers')
        for server in bot.guilds:
                        
            _print(server.id,"initiating starting state")
            # check if server is properly set up
            if (not get_setting(server.id, 'MAINCHANNEL') == get_setting('DEFAULTS', 'MAINCHANNEL')) and is_setup(server.id):
                
                channel = bot.get_channel(get_setting(server.id, 'MAINCHANNEL'))
                
                # delete old messages
                _print(server.id,'Purge old messages')
                await channel.purge(limit=100, check=is_me)
                
                
                # post new message
                _print(server.id,'Post message')
                await postMessage(channel)
                
            else:
                _print(server.id,"Server not fully set up")
        
        _print("main",'------')
        
        _print("main","load looped tasks")
        for server in bot.guilds:
            loadLoopRoutines(server)  
          
        _print("main",'------')  
        
        await bot.change_presence(activity=discord.Game(name='!help'))
        
        initialized = True
        
        _print("main",'Add old roles to timeout check')
        for server in bot.guilds:
            if (not get_setting(server.id, 'MAINCHANNEL') == get_setting('DEFAULTS', 'MAINCHANNEL')) and is_setup(server.id):
                
                channel = bot.get_channel(get_setting(server.id, 'MAINCHANNEL'))
                role1 = get(server.roles, name=get_setting(server.id, 'ROLE_1VS1'))
                role2 = get(server.roles, name=get_setting(server.id, 'ROLE_2VS2'))
                if role1 and role2:
                    
                    for member in server.members:
                        if role1 in member.roles:
                            SERVER_VARS[server.id].singlesDict[member.id] = datetime.datetime.utcnow()
                            await notifySearch(channel, member, role1)
                        if role2 in member.roles:
                            SERVER_VARS[server.id].doublesDict[member.id] = datetime.datetime.utcnow()
                            await notifySearch(channel, member, role2)
        
        _print("main",'------') 
    
    else:
        initialized = False
        _print("main", '------')
        _print("main", 'Restarting after Error')
        _print("main", '------')
        _print("main", 'Logged in as')
        _print("main", bot.user.name)
        _print("main", bot.user.id)
        _print("main", '------')
        
        _print("main","load looped tasks")
        for server in bot.guilds:
            loadLoopRoutines(server)
        
        _print("main",'------')
        for server in bot.guilds:
            if (not get_setting(server.id, 'MAINCHANNEL') == get_setting('DEFAULTS', 'MAINCHANNEL')) and is_setup(server.id):
                channel = bot.get_channel(get_setting(server.id, 'MAINCHANNEL'))
                # post new message
                _print(server.id,'Post message')
                msg = await postMessage(channel)
                SERVER_VARS[server.id].lastMsgStack.append(msg.id)
                
        initialized = True
    _print("main",'Initialization complete')
    _print("main",'------')

@bot.event 
async def on_guild_join(server):
    '''Adds newly added servers to the SERVER_VARS dict and starts their looped tasks.'''
    
    _print(server.id,  "NEW SERVER ARRIVED")
    #add server do global var dict
    global SERVER_VARS
    SERVER_VARS[server.id] = serverNode(server.id)
    
    # ad routines for new server
    loadLoopRoutines(server)
    _print(server.id,  "NEW SERVER INITIALIZED")

@bot.event 
async def on_guild_remove(server):
    '''Removes leaving servers from the SERVER_VARS dict and settings file.'''
    
    _print(server.id,  "SERVER REMOVED")
    # remove server from global var dict
    global SERVER_VARS
    SERVER_VARS.pop(server.id, None)
    
    # remove server from save file
    with open(SETTINGS_FILE, "r+") as read_file:
        data = json.load(read_file)
        
        if server.id in list(data):
            del data[server.id]
            
        read_file.seek(0)
        json.dump(data, read_file, indent=4)
        read_file.truncate()
        
        global SETTINGS
        SETTINGS = data
        
    _print(server.id,  "SAVEDATA CLEARED")

@bot.event
async def on_message(message):
    '''Gets called when messages are posted.
    
    Handles custom commands.
    Counts messages until a new MainMessage has to be posted.
    '''
    
    if initialized and not message.guild == None:
        server = message.guild.id
                
        if (message.channel.id == get_setting(server, 'MAINCHANNEL')):
            SERVER_VARS[server].lastMsgStack.append(message.id)
        
        # ignore own messages
        if message.author == bot.user or message.author.bot:
            return
        
        # check if user is already in a command process
        if message.author in SERVER_VARS[server].cmdLockout:
            #await bot.delete_message(message)
            #await notify(message.channel, "{} bitte warte, bis der letzte Befehl zu Ende ausgeführt wurde.".format(message.author.mention), 7)
            return
        
        # ignore actual commands
        if is_command(message.content, server):
            await bot.process_commands(message)
            return
        # custom command handling
        elif is_custom_command(message.content, server):
            cmdDict = get_setting(server, 'COMMANDS')
            await message.channel.send(cmdDict[message.content[1:]])
            return
        # custom dmcommand handling
        elif is_custom_dmcommand(message.content, server):
            cmdDict = get_setting(server, 'DM_COMMANDS')
            await message.author.send(cmdDict[message.content[1:]])
            # await message.delete()
            return
        
        # post a message after each Nth message in the channel
        if (message.channel.id == get_setting(server, 'MAINCHANNEL')):
            
            SERVER_VARS[server].msgCounter += 1 
            
            #debug
            _print(server, "message counter: (" + str(SERVER_VARS[server].msgCounter) + "/" + str(get_setting(server, 'MESSAGE_INTERVAL')) + ")", log=False)
            
            if SERVER_VARS[server].msgCounter >= get_setting(server, 'MESSAGE_INTERVAL'):
                _print(server, "message counter maximum reached")
                
                lastMsg = None
                try:
                    # this part sometimes raises Internal server errors on discords side.
                    async for msg in message.channel.history(limit=1):
                        lastMsg = msg
                except Exception as e:
                    print(traceback.print_exc())
                    logger.exception("Uncaught exception: {0}".format(str(e)))
                                
                if (lastMsg is not None) and not is_me(lastMsg):
                    
                    await postMessage(message.channel)
                    
                    # reset counter
                    SERVER_VARS[server].msgCounter = 0
                else: 
                    _print(server, "Last message was from bot, waiting for one more.")
        # this line assures, that other commands will be able to run.
        await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    '''Gets called when messages are deleted.
    
    Counts messages until a new MainMessage has to be posted.
    '''
    
    if initialized and not message.guild == None:
        server = message.guild.id
                
        if (message.channel.id == get_setting(server, 'MAINCHANNEL')):
            if message.id in SERVER_VARS[server].lastMsgStack:
                SERVER_VARS[server].lastMsgStack.remove(message.id)

@bot.event
async def on_reaction_add(reaction, user):
    '''Called, when reactions are added.
    
    Handles roling of users reacting to the main message.
    Handles setting of new reactions after performing the set command.
    '''
    
    global SERVER_VARS
    
    if initialized:    
        server = reaction.message.guild.id
        
        # ignore own reactions
        if user == bot.user:
            return
        
        if reaction.message.channel.id == get_setting(server, 'MAINCHANNEL'):
        
            # add roles depending on reactions
            if SERVER_VARS[server].activeMessage:
                if reaction.message.id == SERVER_VARS[server].activeMessage.id:
                    
                    await asyncio.sleep(0.5)            
                    await reaction.message.remove_reaction(reaction.emoji, user)
                                
                    if reaction.emoji == get_setting(server, 'REACTION_1VS1'):
                        role = get(user.guild.roles, name=str(get_setting(server, 'ROLE_1VS1')))
                        await singles(user, role, reaction.message)
                    elif reaction.emoji == get_setting(server, 'REACTION_2VS2'):
                        role = get(user.guild.roles, name=str(get_setting(server, 'ROLE_2VS2')))
                        await doubles(user, role, reaction.message)
        
        # remove search notification on reaction
        #=======================================================================
        # if len(SERVER_VARS[server].searchMessageSinglesDict) + len(SERVER_VARS[server].searchMessageDoublesDict) > 0:
        #     for usrID in SERVER_VARS[server].searchMessageSinglesDict:
        #         if user.id == usrID:
        #             msgID = SERVER_VARS[server].searchMessageSinglesDict[usrID][1]
        #             if msgID == reaction.message.id:
        #                 if reaction.emoji == REACTION_CANCEL:
        #                     role = get(user.guild.roles, name=str(get_setting(server, 'ROLE_1VS1')))
        #                     await singles(user, role, reaction.message)
        #                     break
        #         else:
        #             await reaction.message.remove_reaction(reaction.emoji, user)
        #     
        #     for usrID in SERVER_VARS[server].searchMessageDoublesDict:
        #         if user.id == usrID:
        #             msgID = SERVER_VARS[server].searchMessageDoublesDict[usrID][1]
        #             if msgID == reaction.message.id:
        #                 if reaction.emoji == REACTION_CANCEL:
        #                     role = get(user.guild.roles, name=str(get_setting(server, 'ROLE_2VS2')))
        #                     await doubles(user, role, reaction.message)
        #                     break
        #         else:
        #             await reaction.message.remove_reaction(reaction.emoji, user)
        #=======================================================================
                    
        # handling of change reactions command.
        if SERVER_VARS[server].msg1vs1:
            if reaction.message.id == SERVER_VARS[server].msg1vs1.id :
                if await checkPermissions(user, reaction.message.channel):
                    if reaction.emoji in bot.emojis or isinstance(reaction.emoji, str):
                        _print(server, "updating 1vs1 reaction")
                        
                        # handle custom emoji
                        if not isinstance(reaction.emoji, str):
                            emoji = reaction.emoji.name + ":" + str(reaction.emoji.id)
                        else:
                            emoji = reaction.emoji
                        
                        # update in settings
                        update_settings(server, 'REACTION_1VS1', emoji)
                        
                        await SERVER_VARS[server].msg1vs1.delete()
                        await notify(SERVER_VARS[server].msg1vs1.channel, "{} die 1vs1 Reaktion wurde aktualisiert. ".format(user.mention) + str(reaction.emoji))
                        channel = bot.get_channel(get_setting(server, 'MAINCHANNEL'))
                        await postMessage(channel)
                        SERVER_VARS[server].msg1vs1 = False
                    else:
                        await notify(reaction.message.channel, "{} ich habe leider keinen Zugriff auf dieses Emoji.".format(user.mention))
                else:
                    await asyncio.sleep(0.5)            
                    await reaction.message.remove_reaction(reaction.emoji, user)
        elif SERVER_VARS[server].msg2vs2:
            if reaction.message.id == SERVER_VARS[server].msg2vs2.id:
                if await checkPermissions(user, reaction.message.channel):
                    if reaction.emoji in bot.emojis or isinstance(reaction.emoji, str):
                        _print(server, "updating 2vs2 reaction")
                        
                        # handle custom emoji
                        if not isinstance(reaction.emoji, str):
                            emoji = reaction.emoji.name + ":" + str(reaction.emoji.id)
                        else:
                            emoji = reaction.emoji
                        
                        # update in settings
                        update_settings(server, 'REACTION_2VS2', emoji)
                        
                        await SERVER_VARS[server].msg2vs2.delete()
                        await notify(SERVER_VARS[server].msg2vs2.channel, "{} die 2vs2 Reaktion wurde aktualisiert. ".format(user.mention) + str(reaction.emoji))
                        channel = bot.get_channel(get_setting(server, 'MAINCHANNEL'))
                        await postMessage(channel)
                        SERVER_VARS[server].msg2vs2 = False
                    else:
                        await notify(reaction.message.channel, "{} ich habe leider keinen Zugriff auf dieses Emoji.".format(user.mention))
                else:
                    await asyncio.sleep(0.5)            
                    await reaction.message.remove_reaction(reaction.emoji, user)

@bot.event
async def on_member_update(before, after):
    '''Adds new members of the matchmaking roles to the tracking dicts.
    Removes members who lost the role.
    '''
    
    if initialized: 
        
        server = after.guild.id
        role1vs1 = get(after.guild.roles, name=str(get_setting(server, 'ROLE_1VS1')))
        role2vs2 = get(after.guild.roles, name=str(get_setting(server, 'ROLE_2VS2')))
        
        global SERVER_VARS
        
        # 1vs1 role changes
        if role1vs1:
            
            # on role add
            if role1vs1 not in before.roles and role1vs1 in after.roles:
                _print(server, "added tracker for 1vs1 timeout: " + str(after.name))
                SERVER_VARS[server].singlesDict[after.id] = datetime.datetime.utcnow()
                
            # on role remove
            if role1vs1 in before.roles and role1vs1 not in after.roles:
                _print(server, "removed tracker for 1vs1 timeout: " + str(after.name))
                SERVER_VARS[server].singlesDict.pop(after.id, None)
                
                # remove old search message
                if after.id in list(SERVER_VARS[server].searchMessageSinglesDict):
                    
                    channel = get(after.guild.channels, id=SERVER_VARS[server].searchMessageSinglesDict[after.id][0])
                    
                    if channel:
                        try:
                            message = await channel.fetch_message(SERVER_VARS[server].searchMessageSinglesDict[after.id][1])
                            await message.delete()
                        except:
                            pass
                            
                    SERVER_VARS[server].searchMessageSinglesDict.pop(after.id, None)
                    
        # 2vs2 role changes
        if role2vs2:
        
            # on role add
            if role2vs2 not in before.roles and role2vs2 in after.roles:
                _print(server, "added tracker for 2vs2 timeout: " + str(after.name))
                SERVER_VARS[server].doublesDict[after.id] = datetime.datetime.utcnow()
                
            # on role remove
            if role2vs2 in before.roles and role2vs2 not in after.roles:
                _print(server, "removed tracker for 2vs2 timeout: " + str(after.name))
                SERVER_VARS[server].doublesDict.pop(after.id, None)
                
                # remove old search message
                if after.id in list(SERVER_VARS[server].searchMessageDoublesDict):
                    
                    channel = get(after.guild.channels, id=SERVER_VARS[server].searchMessageDoublesDict[after.id][0])
                    
                    if channel:
                        try:
                            message = await channel.fetch_message(SERVER_VARS[server].searchMessageDoublesDict[after.id][1])
                            await message.delete()
                        except:
                            pass
                            
                    SERVER_VARS[server].searchMessageDoublesDict.pop(after.id, None)

@bot.event 
async def on_error(event_method, *args, **kwargs):
    '''Custom error handler to log all errors in file.
    Otherwise internal Exceptions wont be logged.
    '''
    
    try:
        raise 
    except Exception as e:
        print(traceback.print_exc())
        logger.exception("Uncaught exception: {0}".format(str(e)))

@bot.event 
async def on_command_error(ctx, exception):
    '''Custom command error handler to log all errors in file.
    Otherwise internal Exceptions wont be logged.
    '''
    
    try:
        raise exception
    except Exception as e:
        print(traceback.print_exc())
        logger.exception("Uncaught exception: {0}".format(str(e)))
#===============================================================================
# commands   
#===============================================================================
    
@bot.command(name="1vs1")
async def _1vs1(ctx):
    '''Command to add user to 1vs1 role, calls singles() method.
    
    :param ctx: context of command call
    '''
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
    role = get(user.guild.roles, name=get_setting(message.guild.id, 'ROLE_1VS1'))
    
    _print(server, str(user.name) + ":" + str(user.id) + " used command: 1vs1")
    
    if is_setup(server):
        if message.channel.id == get_setting(message.guild.id, 'MAINCHANNEL'):
            await singles(user, role, message)
        else:
            await notify(message.channel, "{} in diesem Kanal nicht möglich.".format(user.mention))
    else:
        await notify(message.channel, "{} bitte setze erst die Rollen für 1vs1, 2vs2 und einen Hauptkanal. '!help' für mehr.".format(user.mention), 7)
    
    await message.delete()
    
@bot.command(name="2vs2")
async def _2vs2(ctx):
    '''Command to add user to 2vs2 role, calls doubles() method.
    
    :param ctx: context of command call
    '''
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
    role = get(user.guild.roles, name=get_setting(message.guild.id, 'ROLE_2VS2'))
        
    _print(server, str(user.name) + ":" + str(user.id) + " used command: 2vs2")
    
    if is_setup(server):
        if message.channel.id == get_setting(message.guild.id, 'MAINCHANNEL'):
            await doubles(user, role, message)
        else:
            await notify(message.channel, "{} in diesem Kanal nicht möglich.".format(user.mention))
    else:
        await notify(message.channel, "{} bitte setze erst die Rollen für 1vs1, 2vs2 und einen Hauptkanal. '!help' für mehr.".format(user.mention), 7)
    
    await message.delete()

@bot.command()
async def mainChannel(ctx):
    '''Command to set a main channel.
    
    :param ctx: context of command call
    '''
    
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
    
    global SERVER_VARS
    
    SERVER_VARS[server].cmdLockout.append(user)
    
    if await checkPermissions(user, message.channel):
        
        _print(server, str(user.name) + ":" + str(user.id) + " used command: mainChannel")
        
        if not get_setting(message.guild.id, 'ROLE_2VS2') == get_setting('DEFAULTS', 'ROLE_2VS2') and not get_setting(message.guild.id, 'ROLE_1VS1') == get_setting('DEFAULTS', 'ROLE_1VS1'):
            newMainChannel = message.channel
            if not newMainChannel.id == get_setting(server, 'MAINCHANNEL'):
                
                _print(server, 'Apply new main channel')
                oldChannel = bot.get_channel(get_setting(server, 'MAINCHANNEL'))
                update_settings(server, 'MAINCHANNEL', newMainChannel.id)
                
                
                if not oldChannel:
                    _print(server, 'Purge old messages')
                    #first instance of setting main channel
                    await newMainChannel.purge(limit=100, check=is_me)
                    
                _print(server, 'Post new Message')
                await postMessage(newMainChannel)
                
                if oldChannel:
                    _print(server, 'Purge old messages')
                    await oldChannel.purge(limit=100, check=is_me)
                
            else:
                await notify(message.channel, "{} dies ist bereits der Main Channel.".format(user.mention))
        else:
            await notify(message.channel, "{} bitte setze erst die Rollen für 1vs1 und 2vs2. '!help' für mehr.".format(user.mention), 7)
    await message.delete()
    
    if user in SERVER_VARS[server].cmdLockout:
        SERVER_VARS[server].cmdLockout.remove(user)
        
@bot.command(name="set")
async def _set(ctx, *args):
    '''Command to set the different Settings.
    view help command for more.
    
    :param ctx: context of command call
    '''
        
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
    
    repost = False
    cleanup = [message]
    
    global SERVER_VARS
    
    if await checkPermissions(user, message.channel):
        error = ""
        _print(server, str(user.name) + ":" + str(user.id) + " used command: set " + " ".join(args))
                
        if len(args) > 0:
            
            
            
            
            if args[0] == 'prefix':
                #===============================================================
                # PREFIX handling
                #===============================================================
                
                if len(args) == 2:
                    if len(args[1]) == 1:
                        
                        update_settings(server, 'PREFIX', args[1])
                        error = "{} das Prefix wurde aktualisiert. neues Prefix: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "\""
                    
                    else:
                        error = "{} das Prefix muss aus einem Zeichen bestehen. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set prefix !\""
                else:
                    error = "{} falche Anzahl von Argumenten. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set prefix !\""
            
            
            
            
            elif args[0] == 'message' :
                if len(args) == 1:
                    # no arguments given
                    error = "{} fehlendes Argument. Mögliche Argumente: content, timer, interval".format(user.mention) 
                
                
                elif args[1] == 'content':
                    #===============================================================
                    # MESSAGE_CONTENT handling
                    #===============================================================
                    SERVER_VARS[server].cmdLockout.append(user)
                    
                    botPrompt = await message.channel.send("{} Deine nächste Nachricht in diesem Kanal wird als Bot-Hauptnachricht übernommen. \nUm den Vorgang abzubrechen, einfach mit \"stop\" antworten.".format(user.mention))
                    
                    def check_1(m):
                        return m.author == user and m.channel == message.channel
                    
                    try:
                        newMessage = await bot.wait_for('message', timeout = 120, check=check_1)
                    except asyncio.TimeoutError:
                        newMessage = None
                    
                    cleanup.append(botPrompt)
                    
                    if newMessage:
                        cleanup.append(newMessage)
                    
                        # darf nicht mit prefix beginnen.
                        if not newMessage.content[0] == str(get_setting(server, 'PREFIX')):
                            if not newMessage.content == "stop":               
                                # update settings
                                update_settings(server, 'MESSAGE_CONTENT', newMessage.content)
                                
                                repost = True
                                
                                error = "{} die Nachricht wurde aktualisiert.".format(user.mention)
                            
                            else:
                                error = "{} die Nachricht wurde nicht aktualisiert.".format(user.mention)
                        else:
                            error = "{} die Nachricht darf nicht mit \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "\" beginnen."
                    else:
                        error = "{} die Anfrage ist nicht rechtzeitig beantwortet worden.".format(user.mention)
                
                elif args[1] == 'timer':
                    #===============================================================
                    # MESSAGE_REPOST_TIME handling
                    #===============================================================
                    
                    if len(args) == 3:
                        
                        # check if number is valid
                        try: 
                            timeInSeconds = int(args[2])
                            update_settings(server, 'MESSAGE_REPOST_TIME', timeInSeconds)
                            
                            timeStr = str(datetime.timedelta(seconds=timeInSeconds))
                                                        
                            error = "{} das Zeitintervall wurde aktualisiert. Neuer post ab jetzt immer in ".format(user.mention) + timeStr
                        
                        except ValueError:
                            error = "{} die Zeit muss als Zahl in Sekunden angegeben werden. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set message timer 600\""
                    else:
                        error = "{} falche Anzahl von Argumenten. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set message timer 600\""
                
                
                elif args[1] == 'interval':
                    #===============================================================
                    # MESSAGE_INTERVAL handling
                    #===============================================================
                    
                    if len(args) == 3:
                        
                        # check if number is valid
                        try: 
                            count = int(args[2])
                            update_settings(server, 'MESSAGE_INTERVAL', count)
                            
                            repost = True
                            
                            error = "{} das Intervall wurde aktualisiert. Neuer Post ab jetzt immer in ".format(user.mention) + str(count) + " Nachrichten."
                        
                        except ValueError:
                            error = "{} bitte gebe eine Zahl an. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set message interval 20\""
                    else:
                        error = "{} falche Anzahl von Argumenten. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set message interval 20\""
                else:
                    error = "{} falsches Argument. Mögliche Argumente: content, timer, interval".format(user.mention)
                
            
            
            
            elif args[0] == 'reaction':
                #===============================================================
                # REACTION_XVSX handling
                #===============================================================
                
                if len(args) == 1:
                    error = "{} fehlendes Argument. Mögliche Argumente: 1vs1, 2vs2".format(user.mention)
                     
                elif args[1] == '1vs1':
                    react1vs1 = await message.channel.send("{} bitte reagiere mit der gewünschten 1vs1 Reaktion.".format(user.mention))
                    SERVER_VARS[server].msg1vs1 = react1vs1
                    
                elif args[1] == '2vs2':
                    react2vs2 = await message.channel.send("{} bitte reagiere mit der gewünschten 2vs2 Reaktion.".format(user.mention))
                    SERVER_VARS[server].msg2vs2 = react2vs2
                    
                    # the rest of the implementation can be found in on_reaction_add
                else:
                    error = "{} fehlerhafte Argumente. Mögliche Argumente: 1vs1, 2vs2".format(user.mention) 
            
            
            
            
            elif args[0] == 'role':
                #===============================================================
                # ROLE_XVSX handling
                #===============================================================
                                
                if len(args) == 1:
                    error = "{} fehlendes Argument. Mögliche Argumente: 1vs1, 2vs2, timeout".format(user.mention)
                elif len(args) == 2 and (args[1] == '1vs1' or args[1] == '2vs2'):
                    error = "{} fehlendes Argument. bitte gebe den Namen der Rolle an. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set role 1vs1 rollenname\""
                     
                elif args[1] == '1vs1':
                    
                    roleName = " ".join(args[2:])
                    
                    if not roleName == get_setting(message.guild.id, 'ROLE_2VS2'):
                            
                        role = get(user.guild.roles, name=roleName)
                    
                        if role:
                            # remove old role members
                            for memberID in list(SERVER_VARS[server].singlesDict):
                                
                                member = bot.get_guild(server).get_member(memberID)
                                role = get(member.guild.roles, name=str(get_setting(server, 'ROLE_1VS1')))
                                
                                if member and role:
                                    await member.remove_roles(role)
                                    _print(server, "removed 1vs1 from " + str(member))
                            
                            update_settings(server, 'ROLE_1VS1', roleName)
                            
                            error = "{} neue Rolle für 1vs1 gespeichert: ".format(user.mention) + str(get_setting(server, 'ROLE_1VS1'))
                            
                        else:
                            error = "{} Rolle existiert nicht.".format(user.mention)
                    
                    else:
                        error = "{} 1vs1 und 2vs2 dürfen nicht die gleiche Rolle haben.".format(user.mention)
                        
                elif args[1] == '2vs2':
                    
                    roleName = " ".join(args[2:])
                    
                    if not roleName == get_setting(message.guild.id, 'ROLE_1VS1'):
                          
                        role = get(user.guild.roles, name=roleName)
                    
                        if role:
                            # remove old role members
                            for memberID in list(SERVER_VARS[server].doublesDict):
                                
                                member = bot.get_guild(server).get_member(memberID)
                                role = get(member.guild.roles, name=str(get_setting(server, 'ROLE_2VS2')))
                                
                                if member and role:
                                    await member.remove_roles(role)
                                    _print(server, "removed 2vs2 from " + str(member))
                            
                            update_settings(server, 'ROLE_2VS2', roleName)
                            
                            error = "{} neue Rolle für 2vs2 gespeichert: ".format(user.mention) + str(get_setting(server, 'ROLE_2VS2'))
                            
                        else:
                            error = "{} Rolle existiert nicht.".format(user.mention)
                    else:
                        error = "{} 1vs1 und 2vs2 dürfen nicht die gleiche Rolle haben.".format(user.mention)
                    
                elif args[1] == 'timeout':
                    if len(args) == 3 :
                        
                        # check if number is valid
                        try: 
                            timeInSeconds = int(args[2])
                            update_settings(server, 'ROLE_TIMEOUT', timeInSeconds)
                            
                            timeStr = str(datetime.timedelta(seconds=timeInSeconds))
                            
                            repost = True
                            
                            error = "{} das Zeitintervall wurde aktualisiert. Rollen werden nun wieder entfernt nach: ".format(user.mention) + timeStr
                        
                        except ValueError:
                            error = "{} die Zeit muss als Zahl in Sekunden angegeben werden. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set role timeout 600\""
                                        
                    else:
                        error = "{} fehlerhafte Argumente. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set role timeout 600\""
                else:
                    error = "{} fehlerhafte Argumente. Mögliche Argumente: 1vs1, 2vs2, timeout".format(user.mention)
            
            
            
                
            elif args[0] == 'checkinterval':
                
                if len(args) == 1:
                    error = "{} fehlendes Argument. Mögliche Argumente: roles, message".format(user.mention)
                elif not len(args) == 3:
                    error = "{} fehlerhafte Argumente. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set checkinterval roles 60\""
                    
                elif args[1] == 'roles':
                    #===============================================================
                    # CHECK_INTERVAL_ROLES handling
                    #===============================================================
                    
                    # check if number is valid
                    try: 
                        timeInSeconds = int(args[2])
                        update_settings(server, 'CHECK_INTERVAL_ROLES', timeInSeconds)
                        
                        timeStr = str(datetime.timedelta(seconds=timeInSeconds))
                                                
                        error = "{} das Zeitintervall wurde aktualisiert. Vergebene Rollen werden nun alle ".format(user.mention) + timeStr + " überprüft."
                    
                    except ValueError:
                        error = "{} die Zeit muss als Zahl in Sekunden angegeben werden. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set checkinterval roles 60\""
                                   
                    
                elif args[1] == 'message':
                    #===============================================================
                    # CHECK_INTERVAL_REPOST handling
                    #===============================================================
                    
                    # check if number is valid
                    try: 
                        timeInSeconds = int(args[2])
                        update_settings(server, 'CHECK_INTERVAL_REPOST', timeInSeconds)
                        
                        timeStr = str(datetime.timedelta(seconds=timeInSeconds))
                                                
                        error = "{} das Zeitintervall wurde aktualisiert. Es wird nun alle ".format(user.mention) + timeStr + " überprüft, ob eine neue Nachricht gepostet werden muss."
                    
                    except ValueError:
                        error = "{} die Zeit muss als Zahl in Sekunden angegeben werden. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set checkinterval roles 60\""
                            
                else:
                    error = "{} fehlerhafte Argumente. Mögliche Argumente: roles, message".format(user.mention) 
                
            elif args[0] == 'command':
                #===============================================================
                # CUSTOM_COMMAND handling
                #===============================================================
                SERVER_VARS[server].cmdLockout.append(user)
                
                if len(args) == 2:
                    
                    command = str(args[1])
                    
                    if command not in SERVER_COMMANDS:
                    
                        botPrompt = await message.channel.send("{} Deine nächste Nachricht in diesem Kanal wird als Antwort auf den Befehl \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + command + "\" übernommen.\nUm den Vorgang abzubrechen, einfach mit \"stop\" antworten. \nUm einen alten Befehl zu entfernen, mit \"delete\" antworten.")
                        
                        def check_2(m):
                            return m.author == user and m.channel == message.channel
                        
                        try:
                            newMessage = await bot.wait_for('message', timeout = 120, check=check_2)
                        except asyncio.TimeoutError:
                            newMessage = None
                        
                        cleanup.append(botPrompt)
                        
                        if newMessage:
                            cleanup.append(newMessage)
                        
                            # cannot start with prefix
                            if not newMessage.content[0] == str(get_setting(server, 'PREFIX')):
                                if not newMessage.content == "stop":               
                                    # update settings
                                    update_settings(server, 'COMMANDS', newMessage.content, customCmd=command)
                                                                        
                                    error = "{} der Befehl \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + command + "\" wurde aktualisiert."
                                
                                else:
                                    error = "{} der Befehl wurde nicht aktualisiert.".format(user.mention)
                            else:
                                error = "{} die Nachricht darf nicht mit \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "\" beginnen."
                        else:
                            error = "{} die Anfrage ist nicht rechtzeitig beantwortet worden.".format(user.mention)
                    else:
                        error = "{} dieser Befehl ist reserviert und kann nicht gesetzt werden.".format(user.mention)
                else:
                    error = "{} falche Anzahl von Argumenten. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set command beispielBefehl\""
                
            
            elif args[0] == 'dmcommand':
                #===============================================================
                # CUSTOM_COMMAND_DM handling
                #===============================================================
                SERVER_VARS[server].cmdLockout.append(user)
                
                if len(args) == 2:
                    
                    command = str(args[1])
                    
                    if command not in SERVER_COMMANDS:
                    
                        botPrompt = await message.channel.send("{} Deine nächste Nachricht in diesem Kanal wird als Antwort (Private Nachricht) auf den Befehl \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + command + "\" übernommen.\nUm den Vorgang abzubrechen, einfach mit \"stop\" antworten. \nUm einen alten Befehl zu entfernen, mit \"delete\" antworten.")
                        
                        def check_3(m):
                            return m.author == user and m.channel == message.channel
                        
                        try:
                            newMessage = await bot.wait_for('message', timeout = 120, check=check_3)
                        except asyncio.TimeoutError:
                            newMessage = None
                        
                        cleanup.append(botPrompt)
                        
                        if newMessage:
                            cleanup.append(newMessage)
                        
                            # cannot start with prefix
                            if not newMessage.content[0] == str(get_setting(server, 'PREFIX')):
                                if not newMessage.content == "stop":               
                                    # update settings
                                    update_settings(server, 'DM_COMMANDS', newMessage.content, customDmCmd=command)
                                                                        
                                    error = "{} der Befehl \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + command + "\" wurde aktualisiert."
                                
                                else:
                                    error = "{} der Befehl wurde nicht aktualisiert.".format(user.mention)
                            else:
                                error = "{} die Nachricht darf nicht mit \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "\" beginnen."
                        else:
                            error = "{} die Anfrage ist nicht rechtzeitig beantwortet worden.".format(user.mention)
                    else:
                        error = "{} dieser Befehl ist reserviert und kann nicht gesetzt werden.".format(user.mention)
                else:
                    error = "{} falche Anzahl von Argumenten. Beispiel: \"".format(user.mention) + str(get_setting(server, 'PREFIX')) + "set dmcommand beispielBefehl\""
                
            
                
            else:
                error = "{} fehlerhafte Argumente. Mögliche Argumente: prefix, message, reaction, role, checkinterval, command, dmcommand".format(user.mention)
        else:
            # TODO help here
            error = "{} zu wenig Argumente. Mögliche Argumente: prefix, message, reaction, role, checkinterval, command, dmcommand".format(user.mention)
        
        # notify error, if one occured
        if not error == "":
            await notify(message.channel, error, 5)    
    
    if len(cleanup) > 1:
        await message.channel.delete_messages(cleanup)
    elif len(cleanup) == 1:
        await cleanup[0].delete()
    
    if user in SERVER_VARS[server].cmdLockout:
        SERVER_VARS[server].cmdLockout.remove(user)
    
    # only repost Message neccessary
    if repost:
        channel = bot.get_channel(get_setting(server, 'MAINCHANNEL'))
        await postMessage(channel)

@bot.command(name="get")
async def _get(ctx, *args):
    '''Command to get current state of specific settings.
    
    :param ctx: context of command call
    '''
    
        
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
    
    global SERVER_VARS
    
    cleanup = [message]
    
    if await checkPermissions(user, message.channel):
        
        _print(server, str(user.name) + ":" + str(user.id) + " used command: get " + " ".join(args))
        
        returnStr = ""
        if len(args) > 0:
            
            
            if args[0] == 'prefix':
                #===============================================================
                # PREFIX handling
                #===============================================================
                
                returnStr = "{} Das Prefix lautet: \n".format(user.mention) + str(get_setting(message.guild.id, 'PREFIX'))
            
            elif args[0] == 'message' :
                
                if not len(args) == 2:
                    
                    returnStr = "{} zu wenig Argumente. Mögliche Argumente: content, timer, interval".format(user.mention)
                    
                elif args[1] == 'content':
                    #===============================================================
                    # MESSAGE_CONTENT handling
                    #===============================================================
                    
                    returnStr = "{} Die aktuelle Nachricht lautet: \n".format(user.mention) + str(get_setting(message.guild.id, 'MESSAGE_CONTENT'))
                    
                elif args[1] == 'timer':
                    #===============================================================
                    # MESSAGE_REPOST_TIME handling
                    #===============================================================
                    
                    timeStr = str(datetime.timedelta(seconds=get_setting(message.guild.id, 'MESSAGE_REPOST_TIME')))
                    returnStr = "{} Die Nachricht wird automatisch erneut gepostet nach: \n".format(user.mention) + timeStr
                
                elif args[1] == 'interval':
                    #===============================================================
                    # MESSAGE_INTERVAL handling
                    #===============================================================
                    
                    returnStr = "{} Anzahl der Nachrichten, bis die Bot-Nachticht erneut gepostet wird: \n".format(user.mention) + str(get_setting(message.guild.id, 'MESSAGE_INTERVAL'))
                    
                else:
                    returnStr = "{} fehlerhafte Argumente. Mögliche Argumente: content, timer, interval".format(user.mention)
                
            
            
            
            elif args[0] == 'reaction':
                #===============================================================
                # REACTION_XVSX handling
                #===============================================================
                
                if not len(args) == 2:
                    
                    returnStr = "{} zu wenig Argumente. Mögliche Argumente: 1vs1, 2vs2".format(user.mention)
                     
                elif args[1] == '1vs1':
                    
                    returnStr = "{} Die aktuelle Reaktion für 1vs1: \n".format(user.mention) + str(get_setting(message.guild.id, 'REACTION_1VS1'))
                    
                elif args[1] == '2vs2':
                    
                    returnStr = "{} Die aktuelle Reaktion für 2vs2: \n".format(user.mention) + str(get_setting(message.guild.id, 'REACTION_2VS2'))
                    
                else:
                    returnStr = "{} fehlerhafte Argumente. Mögliche Argumente: 1vs1, 2vs2".format(user.mention)
            
            
            
            
            elif args[0] == 'role':
                #===============================================================
                # ROLE_XVSX handling
                #===============================================================
                                
                if not len(args) == 2:
                    
                    returnStr = "{} zu wenig Argumente. Mögliche Argumente: 1vs1, 2vs2, timeout".format(user.mention)
                    
                elif args[1] == '1vs1':
                    
                    returnStr = "{} Die aktuelle 1vs1 Rolle: \n".format(user.mention) + str(get_setting(message.guild.id, 'ROLE_1VS1'))
                    
                elif args[1] == '2vs2':
                    
                    returnStr = "{} Die aktuelle 2vs2 Rolle: \n".format(user.mention) + str(get_setting(message.guild.id, 'ROLE_2VS2'))
                
                elif args[1] == 'timeout':
                    
                    timeStr = str(datetime.timedelta(seconds=get_setting(message.guild.id, 'ROLE_TIMEOUT')))
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
                    
                    timeStr = str(datetime.timedelta(seconds=get_setting(message.guild.id, 'CHECK_INTERVAL_ROLES')))
                    returnStr = "{} Zeitintervall, in dem die Rollen überprüft werden: \n".format(user.mention) + timeStr  
                    
                elif args[1] == 'message':
                    #===============================================================
                    # CHECK_INTERVAL_REPOST handling
                    #===============================================================
                    
                    timeStr = str(datetime.timedelta(seconds=get_setting(message.guild.id, 'CHECK_INTERVAL_REPOST')))
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
            await notify(message.channel, returnStr, 10)
    if len(cleanup) > 1:
        await message.channel.delete_messages(cleanup)
    elif len(cleanup) == 1:
        await cleanup[0].delete()

@bot.command()
async def reset(ctx):
    '''Command to reset all settings to default.
    Current custom commands will not be removed.
    
    :param ctx: context of command call
    '''
    
     
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
    
    global SERVER_VARS
    
    if await checkPermissions(user, message.channel):
        _print(server, str(user.name) + ":" + str(user.id) + " used command: reset")
        _print(server, "resetting to default.") 
        
        oldMainChannel = bot.get_channel(get_setting(server, 'MAINCHANNEL'))
        saveCMD = False
        saveDmCMD = False
        
        # remove server from save file
        with open(SETTINGS_FILE, "r+") as read_file:
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
            
            global SETTINGS
            SETTINGS = data
            
            if saveCMD:
                update_settings(server, 'COMMANDS', saveCMD)
            if saveDmCMD:
                update_settings(server, 'DM_COMMANDS', saveDmCMD)
        
        if oldMainChannel:
            # delete old messages
            _print(server,'Purge old messages')
            await oldMainChannel.purge(limit=100, check=is_me)
            
        SERVER_VARS[server].activeMessage = False
        
        await notify(message.channel, "{} Einstellungen wurden zurückgesetzt. Bitte erneut den Hauptkanal und die 1vs1/2vs2 Rollen setzen.".format(user.mention), 7)
        
        
    await message.delete()

@bot.command()
async def settings(ctx):
    '''Command to send a direct message to the user containing all current settings.
    
    :param ctx: context of command call
    '''
    
     
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
     
    if await checkPermissions(user, message.channel):
        
        _print(server, str(user.name) + ":" + str(user.id) + " used command: settings")
        
        MAINCHANNEL = get_setting(server, 'MAINCHANNEL') 
        PREFIX = str(get_setting(server, 'PREFIX'))
        MESSAGE_INTERVAL = get_setting(server, 'MESSAGE_INTERVAL')
        MESSAGE_CONTENT = get_setting(server, 'MESSAGE_CONTENT')
        MESSAGE_REPOST_TIME = get_setting(server, 'MESSAGE_REPOST_TIME')
        REACTION_1VS1 = get_setting(server, 'REACTION_1VS1')
        REACTION_2VS2 = get_setting(server, 'REACTION_2VS2')
        ROLE_1VS1 = str(get_setting(server, 'ROLE_1VS1'))
        ROLE_2VS2 = str(get_setting(server, 'ROLE_2VS2'))
        ROLE_TIMEOUT = get_setting(server, 'ROLE_TIMEOUT')
        CHECK_INTERVAL_ROLES = get_setting(server, 'CHECK_INTERVAL_ROLES')
        CHECK_INTERVAL_REPOST = get_setting(server, 'CHECK_INTERVAL_REPOST')
            
        embed = discord.Embed(title="AKTUELLE EINSTELLUNGEN:", description="Folgene einstellungen wurden vorgenommen:  ", color=0x00ff00)
        
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

@bot.command()
async def commands(ctx, *args):
    '''Command to send a direct message to the user containing all custom commands.
    
    :param ctx: context of command call
    '''
    
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
     
    if await checkPermissions(user, message.channel):
        
        _print(server, str(user.name) + ":" + str(user.id) + " used command: commands")
        prefix = str(get_setting(server, 'PREFIX'))
        cmdDict = get_setting(server, 'COMMANDS')
        dmCmdDict = get_setting(server, 'DM_COMMANDS')
        
        
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
                await notify(message.channel, "{} dieser Befehl existiert nicht.".format(user.mention))
        else:
            await notify(message.channel, "{} dieser Befehl existiert nicht.".format(user.mention))
    await message.delete()

@bot.command()
async def help(ctx, *args):
    '''Command to send a direct message to the user containing all possible commands.
    
    :param ctx: context of command call
    '''
      
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
    
    if await checkPermissions(user, message.channel):
        
        _print(server, str(user.name) + ":" + str(user.id) + " used command: help " + " ".join(args))
        
        prefix = str(get_setting(server, 'PREFIX'))
        
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

@bot.command()
async def post(ctx):
    '''Command to force reposting of the main message.
    
    :param ctx: context of command call
    '''
    
    
    user = ctx.message.author
    message = ctx.message
    server = message.guild.id
    
    if await checkPermissions(user, message.channel):
        if is_setup(server):
            _print(server, str(user.name) + ":" + str(user.id) + " used command: post ")
            
            channel = bot.get_channel(get_setting(server, 'MAINCHANNEL'))
            if channel.id == message.channel.id:
                await postMessage(channel)
            else:
                await notify(message.channel, "{} nur im Hauptkanal möglich.".format(user.mention))
        else:
            await notify(message.channel, "{} bitte setze erst die Rollen für 1vs1, 2vs2 und den Hauptkanal. '!help' für mehr.".format(user.mention), 7)
    await message.delete()

@bot.command()
async def version(ctx):
    '''Command to get current version.
    
    :param ctx: context of command call
    '''
    
    user = ctx.message.author
    message = ctx.message
    server = ctx.message.guild.id
    
    if await checkPermissions(user, message.channel):
        
        _print(server, str(user.name) + ":" + str(user.id) + " used command: version ")
        await notify(message.channel, "Aktuell genutzte Version: " + VERSION, 5) 
    
    await message.delete()

@bot.command()
async def roll(ctx, *args):
    '''Command to roll a random number between 1 and 9.
    
    :param ctx: context of command call
    '''
    
    user = ctx.message.author
    message = ctx.message
    server = ctx.message.guild.id
    
    _print(server, str(user.name) + ":" + str(user.id) + " used command: roll ")
    
    randInt = randint(0, 9)
    await message.channel.send("{} hat eine **".format(user.mention) + str(randInt) + "** gewürfelt.")
    # await message.delete()

@bot.command()
async def restart(ctx):
    '''Command to restart the bot.
    Only Creator has permissions for this as it affects all connected servers.
    
    :param ctx: context of command call
    '''
    
    user = ctx.message.author
    message = ctx.message
    
    if await checkPermissions(user, message.channel, creator=True):
        await message.delete()
        #bot.loop.close()
        #await bot.logout()
        await bot.close()
    else:    
        await message.delete()

@bot.command()
async def reloadSettings(ctx):
    '''Command to reload the settings file.
    Only Creator has permissions for this.
    
    :param ctx: context of command call
    '''
    
    user = ctx.message.author
    message = ctx.message
    
    if await checkPermissions(user, message.channel, creator=True):
        init_settings()
        await message.delete()
    else:    
        await message.delete()

@bot.command()
async def debug(ctx):
    '''Executes debug code.
    
    :param ctx: context of command call
    '''
    
    user = ctx.message.author
    message = ctx.message
    
    if await checkPermissions(user, message.channel, creator=True):
        await message.delete()
        
        bot.dispatch("ready")
        
        
    #await message.delete()

if __name__ == '__main__':      
    try:
        token = open(TOKEN_FILE,"r").readline()
        
        #bot.add_cog(CoinTournament(bot))
        bot.load_extension("Cogs.CoinTournament")
        bot.run(token)
    except Exception as e:
        print(traceback.print_exc())
        logger.exception("Uncaught exception: {0}".format(str(e)))
    
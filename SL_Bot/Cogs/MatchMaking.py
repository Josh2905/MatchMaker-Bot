'''
Created on 09.04.2019

@author: Joshua Esselmann
'''
from discord.ext import commands
import asyncio
from discord.utils import get
import datetime
import traceback
from functools import partial
from collections import deque


class MatchMaking(commands.Cog):
    '''
    classdocs
    '''
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
            self.checkTimeout = False
            self.repostMessage = False
            
    SERVER_VARS = {}
    COG_NAME = "MatchMaking"
    SERVER_COMMANDS = []
    initialized = False
    
    def __init__(self, bot):
        self.bot = bot
        self.controller = self.bot.get_cog('Controller')
    
    def is_setup(self, server):
        '''Return, wether all neccessary settings are set for the bot to be fully functional.
        
        :param server: Server ID
        '''
        
        if str(server) in list(self.controller.SETTINGS) and 'MAINCHANNEL' in list(self.controller.SETTINGS[str(server)]) and 'ROLE_1VS1' in list(self.controller.SETTINGS[str(server)]) and 'ROLE_2VS2' in list(self.controller.SETTINGS[str(server)]):
            return True
        else:
            return False
    
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
    
    async def notifySearch(self, channel, user, role):
        '''Notify a channel that someone is looking for a match.
        
        :param channel: Channel to be notified
        :param user: User in search of a match
        :param role: Role that is searched for
        '''
                
        server = channel.guild.id
        
        role1vs1 = get(channel.guild.roles, name=str(self.controller.get_setting(server, 'ROLE_1VS1')))
        role2vs2 = get(channel.guild.roles, name=str(self.controller.get_setting(server, 'ROLE_2VS2')))
            
        if role == role1vs1:
            alert = "sucht nach einem 1vs1 Match! {}".format(role.mention)
            msg = await channel.send(user.mention + " " + alert)
            # await msg.add_reaction(REACTION_CANCEL)
            self.SERVER_VARS[server].searchMessageSinglesDict[user.id] = (channel.id, msg.id)
        
        elif role == role2vs2:
            alert = "sucht nach einem 2vs2 Match! {}".format(role.mention)
            msg = await channel.send(user.mention + " " + alert)
            # await msg.add_reaction(REACTION_CANCEL)
            self.SERVER_VARS[server].searchMessageDoublesDict[user.id] = (channel.id, msg.id)
    
    async def singles(self, user, role, message):
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
                await self.notify(message.channel, "{} du hast nicht mehr die Rolle ".format(user.mention) + str(self.controller.get_setting(server, 'ROLE_1VS1')) + ".", timeout=5)
                self.controller._print(server, "removed 1vs1 role from " + str(user.name), cog=self.COG_NAME)
            else:
                # grant user role
                await user.add_roles(role)
                await self.notifySearch(message.channel, user, role)
                # await notify(message.channel, "{0} du hast nun die Rolle ".format(user.mention) + str(get_setting(server, 'ROLE_1VS1')) + ".")
                self.controller._print(server, "applied 1vs1 role to " + str(user.name), cog=self.COG_NAME)
        else:
            await self.notify(message.channel, "{0} diese Rolle existiert nicht mehr. Bitte erneut setzen. (!help)".format(user.mention))
        
    async def doubles(self, user, role, message):
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
                await self.notify(message.channel, "{} du hast nicht mehr die Rolle ".format(user.mention) + str(self.controller.get_setting(server, 'ROLE_2VS2')) + ".", timeout=5)
                self.controller._print(server, "removed 2vs2 role from " + str(user.name), cog=self.COG_NAME)
            else:
                # grant user role
                await user.add_roles(role)
                await self.notifySearch(message.channel, user, role)
                # await notify(message.channel, "{} du hast nun die Rolle ".format(user.mention) + str(get_setting(server, 'ROLE_2VS2')) + ".")
                self.controller._print(server, "applied 2vs2 role to " + str(user.name), cog=self.COG_NAME)
        else:
            await self.notify(message.channel, "{0} diese Rolle existiert nicht mehr. Bitte erneut setzen. (!help)".format(user.mention))
    
    async def postMessage(self, channel):
        '''Posts the main matchmaking message to the specified channel.
        removes the old message in the process. Returns new Message.
        
        :param channel: Channel where message will be posted.
        '''
        server = channel.guild.id
        
        if channel and self.controller.is_setup(server):
            
            #remove old message
            if self.SERVER_VARS[server].activeMessage:
                await self.SERVER_VARS[server].activeMessage.delete()
                  
            # send message
            self.SERVER_VARS[server].msgTimer = datetime.datetime.utcnow()
            self.SERVER_VARS[server].msgCounter = 0
            
            msg = await channel.send(self.controller.get_setting(server, 'MESSAGE_CONTENT'))
            self.SERVER_VARS[server].activeMessage = msg
            
            #add reactions
            r1v1 = get(self.bot.emojis, name = self.controller.get_setting(server, 'REACTION_1VS1'))
            if r1v1 == None:
                r1v1 = self.controller.get_setting(server, 'REACTION_1VS1')
            
            
            r2v2 = get(self.bot.emojis, name = self.controller.get_setting(server, 'REACTION_2VS2'))
            if r2v2 == None:
                r2v2 = self.controller.get_setting(server, 'REACTION_2VS2')
            
            await msg.add_reaction(r1v1)
            await msg.add_reaction(r2v2)
            self.controller._print(server, "posting main message", cog=self.COG_NAME)
            
            return msg
            
        else:
            self.controller._print(server, "could not post message: server not fully set up", cog=self.COG_NAME)
            
            return None
    
    def is_command(self, cmd, server):
        '''Return, if a command with this name exists.
        
        :param cmd: Command name
        :param server: Server ID
        '''
        if len(cmd) > 1 and cmd[0] == str(self.controller.get_setting(server, 'PREFIX')):
                
            command = cmd[1:]
            
            mainCommand = command.split(" ", 1)[0]
            
            if mainCommand in self.SERVER_COMMANDS:
                return True
        return False
    
    #===============================================================================
    # looped routines    
    #===============================================================================
                
    async def checkTimeout(self, server):
        '''Periodically checks for role timeouts and removes them if enough time has passed.
        
        :param server: Server ID
        '''
        
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            
            
            if self.controller.initialized and self.is_setup(server) and (not self.controller.get_setting(server, 'MAINCHANNEL') == self.controller.get_setting('DEFAULTS', 'MAINCHANNEL')):
                if len(list(self.SERVER_VARS[server].singlesDict)) + len(list(self.SERVER_VARS[server].doublesDict)) > 0:
                    self.controller._print(server, "checking for role timeouts:", log=False, cog=self.COG_NAME)
                    
                    srvr = self.bot.get_guild(server)
                    
                    for member in list(self.SERVER_VARS[server].singlesDict):
                        difference = datetime.datetime.utcnow() - self.SERVER_VARS[server].singlesDict[member]
                        difference -= datetime.timedelta(microseconds=difference.microseconds)
                        user = get(srvr.members, id=member)
                        self.controller._print(server, "| " + str(user) + " 1vs1 (" + str(difference) + "/" + str(str(datetime.timedelta(seconds=self.controller.get_setting(server, 'ROLE_TIMEOUT')))) + ")", log=False, cog=self.COG_NAME)
                        if difference.total_seconds() > self.controller.get_setting(server, 'ROLE_TIMEOUT'):
                            
                            role = get(srvr.roles, name=str(self.controller.get_setting(server, 'ROLE_1VS1')))
                            
                            try:
                                await user.remove_roles(role)
                            except AttributeError:
                                pass
                            await asyncio.sleep(1)  #needed for no weird behaviour
                            self.controller._print(server, "timeout: removed 1vs1 from " + str(user), cog=self.COG_NAME)
                    
                    for member in list(self.SERVER_VARS[server].doublesDict):
                        difference = datetime.datetime.utcnow() - self.SERVER_VARS[server].doublesDict[member]
                        difference -= datetime.timedelta(microseconds=difference.microseconds)
                        user = get(srvr.members, id=member)
                        self.controller._print(server, str(user) + " 2vs2 (" + str(difference) + "/" + str(str(datetime.timedelta(seconds=self.controller.get_setting(server, 'ROLE_TIMEOUT')))) + ")", log=False, cog=self.COG_NAME)
                        if difference.total_seconds() > self.controllerget_setting(server, 'ROLE_TIMEOUT'):
                            
                            role = get(srvr.roles, name=str(self.controller.get_setting(server, 'ROLE_2VS2')))
                            
                            try:
                                await user.remove_roles(role)
                            except AttributeError:
                                pass
                            await asyncio.sleep(1)
                            self.controller._print(server, "timeout: removed 2vs2 from " + str(user), cog=self.COG_NAME)
                          
            await asyncio.sleep(self.controller.get_setting(server, 'CHECK_INTERVAL_ROLES')) #seconds
    
    async def repostMessage(self, server):
        '''Periodically checks for the repost timeout of the main message and reposts it if enough time has passed.
        
        '''
        
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            
            
            if len(self.SERVER_VARS[server].lastMsgStack) > 0 and self.controller.initialized and self.is_setup(server) and self.SERVER_VARS[server].activeMessage and (not self.controller.get_setting(server, 'MAINCHANNEL') == self.controller.get_setting('DEFAULTS', 'MAINCHANNEL')):
                
                timeDifference = datetime.datetime.utcnow() - self.SERVER_VARS[server].msgTimer
                timeLimit = self.controller.get_setting(server, 'MESSAGE_REPOST_TIME')
                              
                if not (self.SERVER_VARS[server].lastMsgStack[-1] == self.SERVER_VARS[server].activeMessage.id):
                    self.controller._print(server, "checking for message repost timeout (" + str(round(timeDifference.total_seconds(), 2)) + "/" + str(round(timeLimit, 2)) + ")", log=False, cog=self.COG_NAME)
                else:
                    self.SERVER_VARS[server].msgTimer = datetime.datetime.utcnow()
                
                
                if timeDifference.total_seconds() > timeLimit:          
                
                    channel = self.bot.get_channel(self.controller.get_setting(server, 'MAINCHANNEL'))
                    
                    lastMsg = None
                    
                    try:
                        lastMsg = await channel.fetch_message(self.SERVER_VARS[server].lastMsgStack[-1])
                    except IndexError:
                        pass
                    except Exception as e:
                        print(traceback.print_exc())
                        self.controller.logger.exception("Uncaught exception: {0}".format(str(e)))
                    
                    if lastMsg is not None:
                                            
                        if (not lastMsg.id == self.SERVER_VARS[server].activeMessage.id) and (not self.controller.is_command(lastMsg.content, server)) and (not self.controller.is_custom_command(lastMsg.content, server)):
                            
                            if self.is_me(lastMsg):
                                differenceToLastMsg = lastMsg.created_at - self.SERVER_VARS[server].msgTimer #timezone correction
                                # if last msg was posted by bot, it takes at least 7 minutes to have discord display them as seperate messages.
                                timeLimit = 430 + differenceToLastMsg.total_seconds()
                                self.controller._print(server,"prolonging time limit to seperate messages (" + str(round(timeDifference.total_seconds(), 2)) + "/" + str(round(timeLimit, 2)) + ")", log=False, cog=self.COG_NAME)
                            
                            if timeDifference.total_seconds() > timeLimit:
                                self.controller._print(server, "timeout: Reposting Message", cog=self.COG_NAME)
                                await self.postMessage(channel)
                        
                        else:
                            self.SERVER_VARS[server].msgTimer = datetime.datetime.utcnow()
                    
            await asyncio.sleep(self.controller.get_setting(server, 'CHECK_INTERVAL_REPOST'))
        
    def loadLoopRoutines(self, server):    
        '''Loads Eventloop tasks for a server.
        
        :param server: Server
        '''
        
        def callback_checkTimeout(serverID, task):
            self.SERVER_VARS[serverID].checkTimeout = False
            self.controller._print(server.id, "checkTimeout coro stopped \n!\n!\n!", cog=self.COG_NAME)
        def callback_repostMessage(serverID, task):
            self.SERVER_VARS[serverID].repostMessage = False
            self.controller._print(server.id, "repostMessage coro stopped \n!\n!\n!", cog=self.COG_NAME)
        
        # add looped tasks to bot.
        if not self.SERVER_VARS[server.id].checkTimeout:
            future1 = self.bot.loop.create_task(self.checkTimeout(server.id))
            future1.add_done_callback(partial(callback_checkTimeout, server.id))
            self.SERVER_VARS[server.id].checkTimeout = True
            self.controller._print(server.id, "checkTimeout coro created", cog=self.COG_NAME)
        
        if not self.SERVER_VARS[server.id].repostMessage:
            future2 = self.bot.loop.create_task(self.repostMessage(server.id))
            future2.add_done_callback(partial(callback_repostMessage, server.id))
            self.SERVER_VARS[server.id].repostMessage = True
            self.controller._print(server.id, "repostMessage coro created", cog=self.COG_NAME)
        
        if True:
            pass

    #===============================================================================
    # called in on_ready of controller  
    #===============================================================================
    
    async def initialize(self):
        self.controller._print("init",'initializing', cog=self.COG_NAME)
        
        # initialize MainChannels
        for server in self.bot.guilds:
                        
            self.controller._print(server.id,"initiating starting state", cog=self.COG_NAME)
            # check if server is properly set up
            if (not self.controller.get_setting(server.id, 'MAINCHANNEL') == self.controller.get_setting('DEFAULTS', 'MAINCHANNEL')) and self.is_setup(server.id):
                
                channel = self.bot.get_channel(self.controller.get_setting(server.id, 'MAINCHANNEL'))
                
                # delete old messages
                self.controller._print(server.id,'Purge old messages', cog=self.COG_NAME)
                await channel.purge(limit=100, check=self.is_me)
                
                
                # post new message
                self.controller._print(server.id,'Post message', cog=self.COG_NAME)
                await self.postMessage(channel)
                
            else:
                self.controller._print(server.id,"Matchmaking not fully set up", cog=self.COG_NAME)
        
        self._print("init",'------', cog=self.COG_NAME)
        
        self._print("init","load looped tasks", cog=self.COG_NAME)
        
        for server in self.bot.guilds:
            self.loadLoopRoutines(server)  
          
        self.controller._print("init",'------', cog=self.COG_NAME)  
        
        self.controller._print("init",'Add old roles to timeout check', cog=self.COG_NAME)
            
        for server in self.bot.guilds:
            if (not self.controller.get_setting(server.id, 'MAINCHANNEL') == self.controller.get_setting('DEFAULTS', 'MAINCHANNEL')) and self.is_setup(server.id):
                
                channel = self.bot.get_channel(self.controller.get_setting(server.id, 'MAINCHANNEL'))
                role1 = get(server.roles, name=self.controller.get_setting(server.id, 'ROLE_1VS1'))
                role2 = get(server.roles, name=self.controller.get_setting(server.id, 'ROLE_2VS2'))
                if role1 and role2:
                    
                    for member in server.members:
                        if role1 in member.roles:
                            self.SERVER_VARS[server.id].singlesDict[member.id] = datetime.datetime.utcnow()
                            await self.notifySearch(channel, member, role1)
                        if role2 in member.roles:
                            self.SERVER_VARS[server.id].doublesDict[member.id] = datetime.datetime.utcnow()
                            await self.notifySearch(channel, member, role2)
        
        self.controller._print("init",'------', cog=self.COG_NAME)
        
        self.initialized = True
        self.controller._print("init",'Cog Initialized', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME) 
 
    async def init_on_error(self):
        
        self.initialized = False
        self._print("init","load looped tasks", cog=self.COG_NAME)
        for server in self.bot.guilds:
            self.loadLoopRoutines(server)
        
        self._print("init",'------', cog=self.COG_NAME)
        
        self._print("init",'posting messages:', cog=self.COG_NAME)
       
        for server in self.bot.guilds:
            if (not self.controller.get_setting(server.id, 'MAINCHANNEL') == self.controller.get_setting('DEFAULTS', 'MAINCHANNEL')) and self.is_setup(server.id):
                channel = self.bot.get_channel(self.controller.get_setting(server.id, 'MAINCHANNEL'))
                # post new message
                self.controller._print(server.id,'Post message', cog=self.COG_NAME)
                msg = await self.postMessage(channel)
                self.SERVER_VARS[server.id].lastMsgStack.append(msg.id)
        
        self.controller._print("init",'------', cog=self.COG_NAME)
        self.initialized = True
        self.controller._print("init",'Cog Initialized', cog=self.COG_NAME)
        self.controller._print("init",'------', cog=self.COG_NAME) 
        if True:
            pass
    
    #===============================================================================
    # Events
    #===============================================================================
    
    @commands.Cog.listener()
    async def on_guild_join(self, server):
        self.controller._print(server.id,'loading looped routines', cog=self.COG_NAME)
        self.loadLoopRoutines(server)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        '''Gets called when messages are posted.
        
        Counts messages until a new MainMessage has to be posted.
        '''
        if self.initialized and not message.guild == None:
            server = message.guild.id
            
            #keep track of last message
            if (message.channel.id == self.controller.get_setting(server, 'MAINCHANNEL')):
                self.SERVER_VARS[server].lastMsgStack.append(message.id)
                
            # ignore own messages
            if message.author == self.bot.user or message.author.bot:
                return
            
            # check if user is already in a command process
            if message.author in self.controller.SERVER_VARS[server].cmdLockout:
                return    
            
            # ignore actual commands
            if self.is_command(message.content, server):
                return    
            
            # post a message after each Nth message in the channel
            if (message.channel.id == self.controller.get_setting(server, 'MAINCHANNEL')):
                
                self.SERVER_VARS[server].msgCounter += 1 
                
                #debug
                self.controller._print(server, "message counter: (" + str(self.SERVER_VARS[server].msgCounter) + "/" + str(self.controller.get_setting(server, 'MESSAGE_INTERVAL')) + ")", log=False, cog=self.COG_NAME)
                
                if self.SERVER_VARS[server].msgCounter >= self.controller.get_setting(server, 'MESSAGE_INTERVAL'):
                    self.controller._print(server, "message counter maximum reached", cog=self.COG_NAME)
                    
                    lastMsg = None
                    try:
                        # this part sometimes raises Internal server errors on discords side.
                        async for msg in message.channel.history(limit=1):
                            lastMsg = msg
                    except Exception as e:
                        print(traceback.print_exc())
                        self.controller.logger.exception("Uncaught exception: {0}".format(str(e)))
                                    
                    if (lastMsg is not None) and not self.controller.is_me(lastMsg):
                        
                        await self.postMessage(message.channel)
                        
                        # reset counter
                        self.SERVER_VARS[server].msgCounter = 0
                    else: 
                        self.controller._print(server, "Last message was from bot, waiting for one more.", cog=self.COG_NAME)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        '''Gets called when messages are deleted.
        
        removes messages from lastMsgStack.
        '''
        
        if self.initialized and not message.guild == None:
            server = message.guild.id
                    
            if (message.channel.id == self.controller.get_setting(server, 'MAINCHANNEL')):
                if message.id in self.SERVER_VARS[server].lastMsgStack:
                    self.SERVER_VARS[server].lastMsgStack.remove(message.id)
                
    @commands.command()
    async def testdebug(self, ctx):
        """Says hello"""
        member = ctx.author
        server = ctx.server.id
        await ctx.send("" + self.controller.get_setting("MAINCHANNEL") + " || " + self.controller.self.bot.SERVER_VARS[server])
    
def setup(bot):
    bot.add_cog(MatchMaking(bot))
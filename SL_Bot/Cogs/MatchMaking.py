'''
Created on 09.04.2019

@author: Joshua Esselmann
'''
from discord.ext import commands
import asyncio
from discord.utils import get
import datetime

class MatchMaking(commands.Cog):
    '''
    classdocs
    '''


    def __init__(self, bot):
        self.bot = bot
    
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
        
        role1vs1 = get(channel.guild.roles, name=str(self.bot.get_setting(server, 'ROLE_1VS1')))
        role2vs2 = get(channel.guild.roles, name=str(self.bot.get_setting(server, 'ROLE_2VS2')))
            
        if role == role1vs1:
            alert = "sucht nach einem 1vs1 Match! {}".format(role.mention)
            msg = await channel.send(user.mention + " " + alert)
            # await msg.add_reaction(REACTION_CANCEL)
            self.bot.SERVER_VARS[server].searchMessageSinglesDict[user.id] = (channel.id, msg.id)
        
        elif role == role2vs2:
            alert = "sucht nach einem 2vs2 Match! {}".format(role.mention)
            msg = await channel.send(user.mention + " " + alert)
            # await msg.add_reaction(REACTION_CANCEL)
            self.bot.SERVER_VARS[server].searchMessageDoublesDict[user.id] = (channel.id, msg.id)
    
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
                await self.notify(message.channel, "{} du hast nicht mehr die Rolle ".format(user.mention) + str(self.bot.get_setting(server, 'ROLE_1VS1')) + ".", timeout=5)
                self.bot._print(server, "removed 1vs1 role from " + str(user.name))
            else:
                # grant user role
                await user.add_roles(role)
                await self.notifySearch(message.channel, user, role)
                # await notify(message.channel, "{0} du hast nun die Rolle ".format(user.mention) + str(get_setting(server, 'ROLE_1VS1')) + ".")
                self.bot._print(server, "applied 1vs1 role to " + str(user.name))
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
                await self.notify(message.channel, "{} du hast nicht mehr die Rolle ".format(user.mention) + str(self.bot.get_setting(server, 'ROLE_2VS2')) + ".", timeout=5)
                self.bot._print(server, "removed 2vs2 role from " + str(user.name))
            else:
                # grant user role
                await user.add_roles(role)
                await self.notifySearch(message.channel, user, role)
                # await notify(message.channel, "{} du hast nun die Rolle ".format(user.mention) + str(get_setting(server, 'ROLE_2VS2')) + ".")
                self.bot._print(server, "applied 2vs2 role to " + str(user.name))
        else:
            await self.notify(message.channel, "{0} diese Rolle existiert nicht mehr. Bitte erneut setzen. (!help)".format(user.mention))
    
    async def postMessage(self, channel):
        '''Posts the main matchmaking message to the specified channel.
        removes the old message in the process. Returns new Message.
        
        :param channel: Channel where message will be posted.
        '''
        server = channel.guild.id
        
        if channel and self.bot.is_setup(server):
            
            #remove old message
            if self.bot.SERVER_VARS[server].activeMessage:
                await self.bot.SERVER_VARS[server].activeMessage.delete()
                  
            # send message
            self.bot.SERVER_VARS[server].msgTimer = datetime.datetime.utcnow()
            self.bot.SERVER_VARS[server].msgCounter = 0
            
            msg = await channel.send(self.bot.get_setting(server, 'MESSAGE_CONTENT'))
            self.bot.SERVER_VARS[server].activeMessage = msg
            
            #add reactions
            r1v1 = get(self.bot.emojis, name = self.bot.get_setting(server, 'REACTION_1VS1'))
            if r1v1 == None:
                r1v1 = self.bot.get_setting(server, 'REACTION_1VS1')
            
            
            r2v2 = get(self.bot.emojis, name = self.bot.get_setting(server, 'REACTION_2VS2'))
            if r2v2 == None:
                r2v2 = self.bot.get_setting(server, 'REACTION_2VS2')
            
            await msg.add_reaction(r1v1)
            await msg.add_reaction(r2v2)
            self.bot._print(server, "posting main message")
            
            return msg
            
        else:
            self.bot._print(server, "could not post message: server not fully set up")
            
            return None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            await channel.send('Welcome {0.mention}.'.format(member))

    @commands.command()
    async def testdebug(self, ctx):
        """Says hello"""
        member = ctx.author
        server = ctx.server.id
        await ctx.send("" + self.bot.get_setting("MAINCHANNEL") + " || " + self.bot.self.bot.SERVER_VARS[server])
    
def setup(bot):
    bot.add_cog(MatchMaking(bot))
'''
Created on 25.02.2019

@author: Joshua Esselmann
@version: 1.2.0
'''


import json
import traceback

from discord.ext import commands

SETTINGS_FILE = 'settings.json'
TOKEN_FILE = 'token.txt'
EXTENSIONS = ["Cogs.Controller", "Cogs.MatchMaking"]
COMMANDS = ["1vs1","2vs2","mainChannel","set","get","reset", "settings", "post", "commands", "help", "version", "restart", "roll", "reloadSettings"]
    

# dynamic prefixes
def get_prefix(bot, message):
    '''This method enables the use of custom Prefixes set by the user.'''
    if message.guild is not None:
        serverid = str(message.guild.id)
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        
        if serverid in list(data) and 'PREFIX' in list(data[serverid]):
            prefix = data[serverid]['PREFIX']
        else:
            prefix = "!"
    else:
        prefix = "!"
    return prefix

bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')

def is_command(cmd):
    '''Return, if a command with this name exists.
    
    :param cmd: Command name
    :param server: Server ID
    '''
    if len(cmd.content) > 1 and cmd.content[0] == str(get_prefix(bot, cmd)):
            
        command = cmd.content[1:]
        
        mainCommand = command.split(" ", 1)[0]
        
        if mainCommand in COMMANDS:
            return True
    return False

@bot.event
async def on_message(message):
    if is_command(message):
        await bot.process_commands(message)

if __name__ == '__main__':      
    try:
        token = open(TOKEN_FILE,"r").readline()
        
        for ext in EXTENSIONS:
            bot.load_extension(ext)
        bot.run(token)
    except Exception as e:
        print(traceback.print_exc())
    
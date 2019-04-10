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

# dynamic prefixes
def get_prefix(bot, message):
    '''This method enables the use of custom Prefixes set by the user.'''
    serverid = str(message.guild.id)
    with open(SETTINGS_FILE) as f:
        data = json.load(f)
    
    if serverid in list(data) and 'PREFIX' in list(data[serverid]):
        prefix = data[serverid]['PREFIX']
    else:
        prefix = "!"
    
    return prefix

bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')


if __name__ == '__main__':      
    try:
        token = open(TOKEN_FILE,"r").readline()
        
        for ext in EXTENSIONS:
            bot.load_extension(ext)
        bot.run(token)
    except Exception as e:
        print(traceback.print_exc())
    
'''
Created on 10.04.2019

@author: Joshua Esselmann
'''
from _collections import deque
import datetime

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
    
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       authentication.py
#
#       Copyright 2010 Jelle Smet <web@smetj.net>
#
#       This file is part of Monitoring python library.
#
#           Monitoring python library is free software: you can redistribute it and/or modify
#           it under the terms of the GNU General Public License as published by
#           the Free Software Foundation, either version 3 of the License, or
#           (at your option) any later version.
#
#           Monitoring python library is distributed in the hope that it will be useful,
#           but WITHOUT ANY WARRANTY; without even the implied warranty of
#           MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#           GNU General Public License for more details.
#
#           You should have received a copy of the GNU General Public License
#           along with Monitoring python library.  If not, see <http://www.gnu.org/licenses/>.
import hashlib
import pexpect

class Authenticate:
    '''Class providing authentication.'''
    def __init__(self,auth_type='default',database={},logger=None):
        self.auth_type=auth_type
        self.database=database
        self.logger=logger
        self.logger.info("Authentication method initiated of type: %s"%(self.auth_type))
    def do(self,username,password):
        '''Execute the authentication based upon type chosen at init.'''
        if self.auth_type == 'none':
            return True
        if username != None and password != None and username != '' and password != '':
            if self.auth_type == 'default':
                return self.__default(username=username,password=password)
            elif self.auth_type == 'pam':
                return self.__pam(username=username,password=password)
            else:
                self.logger.warn("Unknown authentication method.")
        else:
            self.logger.warn("Username or password can't be None or empty when authentication type is different than none.")
            return False
    def __default(self,username,password):
        '''Accepts username and password and depending upon the the auth style defined at init an auth type is chosen.'''
        if self.database.has_key(username):
            hash = hashlib.md5()
            hash.update(password+'\n')
            if hash.hexdigest() == self.database[username]:
                self.logger.info("Authentication succeeded for user %s."%(username))
                return True
            else:
                self.logger.warn("Authentication failed for user %s."%(username))
                return False
        else:
            self.logger.warn("User %s is not defined."%(username))
            return False
    def __pam(self, username, password):
        '''Accepts username and password and tried to use PAM for authentication'''
        child=None
        try:
            child = pexpect.spawn('/bin/su - %s'%(username))
            child.expect('Password:')
            child.sendline(password)
            #result=child.expect([username,'su: Authentication failure',pexpect.EOF])
            result=child.expect(username)
            child.close()
        except Exception as err:
            if child != None:
                child.close()
            self.logger.warn("Pam authentication failed.")
            return False
        if result == 0:
            self.logger.info("Authentication succeeded for user %s."%(username))
            return True
        else:
            self.logger.info("Authentication failed for user %s."%(username))
            return False

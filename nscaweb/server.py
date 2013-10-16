#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       server.py
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
import threading
import Queue
import os
import sys
import signal
import time
from time import gmtime
from configobj import ConfigObj

class ThreadControl():
    def __init__(self):
        self.ignition_key=True
        self.last_ignition_key=True
        self.threads={}
        self.queues={}

    def key(self):
        return self.ignition_key

    def block(self):
        return self.ignition_key

    def last_block(self):
        return self.last_ignition_key

    def stop_all(self,list):
        self.ignition_key=False
        for group in list:
            for thread in group:
                try:
                    group[thread].stop()
                except:
                    pass
                if group[thread].loop and group[thread].name != 'last' and group[thread].is_alive():
                    return False
        self.last_ignition_key=False
        time.sleep(1)


class ConfigFileMonitor(threading.Thread):
    '''Monitors if the configfile has changed and if so, reads it.'''

    def __init__(self,file,logger,blockcallback):
        threading.Thread.__init__(self)
        self.config_file=file
        self.logger=logger
        self.loop=blockcallback

        try:
            self.file=ConfigObj(self.config_file)
        except Exception as err:
            sys.stderr.write('There appears to be an error in your configfile:\n')
            sys.stderr.write('\t'+ str(type(err))+" "+str(err) + "\n" )
            os.kill(os.getpid(),signal.SIGKILL)

        self.file_stats     =os.stat(self.config_file)
        self.current_stats  =os.stat(self.config_file)
        self.daemon=True
        self.start()

    def run(self):
        self.logger.info("ConfigFileMonitor thread started.")
        while self.loop.block()==True:
            self.current_stats  =os.stat(self.config_file)
            if (self.current_stats.st_ctime != self.file_stats.st_ctime):
                try:
                    self.file_stats=self.current_stats
                    self.logger.info("The config file has changed.")
                    self.config=ConfigObj(self.config_file)
                    self.logger.info("The config file is reloaded.")
                except:
                    self.logger.error("The config file has not been loaded as it contains errors.")
                    previous_value=current_value
            time.sleep(1)
        self.logger.info("ConfigFileMonitor thread stopped.")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       communication.py
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
import socket
import os
import threading
import time
import random
import Queue
from stat import ST_MODE,S_ISFIFO
from urllib import urlencode
import urllib2
from xml.etree import ElementTree
from hashlib import md5
import sys

class LoadBalance():
    '''Accepts a list of destinations (ip/hostnames) and chooses based upon self.style an ip address.
    There is no sanitiy checking done on the input.  You could provide a list of dog names if you want.
    The style of selection is defined at init.'''
    def __init__(self,style='random'):
        '''By default a randon style selection is done. '''
        self.style=style
        self.previous_destination=None
    def choose(self,destinations):
        '''Accepts a list of destinations and returns a value from it based upon the style chosen on init.'''
        if self.style=='random':
            return destinations[random.randint(0,len(destinations)-1)]
        elif self.style=='next':
            if self.previous_destination == None or self.previous_destination == len(destinations)-1:
                self.previous_destination=0
            else:
                self.previous_destination+=1
            return destinations[self.previous_destination]
        elif self.style=='first':
            return destinations[0]
class Lookup():
    '''Accepts a string, checks if it's a valid ip address, does a reverse lookup and returns the hostname.  If this fails, the original input is returned.'''
    def __init__(self):
        pass
    def reverse(self,ip=None):
        try:
            socket.inet_aton(ip)
            hostname = socket.gethostbyaddr(ip)
            return hostname.lower()
        except socket.error:
            return ip.lower()
class SubmitListener(threading.Thread):
    '''A thread which monitors the input_queue for data and submits this to the correct OutputQueue, and if that doesn't exist, it creates a new OutputQueue object
    The format of the packages to dump into self.input_queue:
    {"destination":{
        "type":"file",
        "locations":[ "/tmp/moncli_output1.txt","/tmp/moncli_output2.txt" ],
        "username":"default",
        "password":"changeme"
        "token":"fubar"},
    "requestUUID":uuid
    "data":"what to write to command pipe"
      }'''

    def __init__(self,timeout=60,retries=5,chunks=1000,quota=0,logger=None,blockcallback=None):
        threading.Thread.__init__(self)
        self.timeout=timeout
        self.retries=retries
        self.chunks=chunks
        self.quota=quota
        self.logger=logger
        self.loop=blockcallback
        self.input_queue=Queue.Queue(0)
        self.output_queues={}
        self.logger.info("SubmitListener thread started.")
        self.daemon=True
        self.start()
    def run(self):
        while self.loop.block() == True:
            while not self.input_queue.empty():
                package=self.input_queue.get()
                if package['external_command'] == None or package['external_command'] == '':
                    self.logger.error("Request %s produced no output.  It's purged."%(package.get('requestUUID','?')))
                else:
                    self.__submit(package)
            time.sleep(0.1)
        self.logger.info("SubmitListener thread stopped.")
    def dump(self,package):
        '''Using dump, the average package size is calculated prior to submitting it to the Queue.  This is the preferred way for writing data ino SubmitListener.'''
        queue_name = self.__queue_name(package['destination'])

        #If we don't have a queue like that create a new one
        if not self.output_queues.has_key(queue_name):
            self.output_queues[queue_name] = OutputQueue(   name=queue_name,
                                    destination=package['destination'],
                                    timeout=self.timeout,
                                    retries=self.retries,
                                    chunks=self.chunks,
                                    logger=self.logger,
                                    blockcallback=self.loop)

        if self.quota > 0:
            if self.output_queues[queue_name].avg_data_size * self.output_queues[queue_name].queue.qsize() < self.quota:
                #Keep track of the average data size
                self.output_queues[queue_name].avg_data_size=(self.output_queues[queue_name].avg_data_size+int(sys.getsizeof(package['external_command'])))/2
                self.output_queues[queue_name].queue.put(package['external_command'])
            else:
                raise Exception('queue oversized')
        else:
            self.output_queues[queue_name].avg_data_size=(self.output_queues[queue_name].avg_data_size+int(sys.getsizeof(package['external_command'])))/2
            self.output_queues[queue_name].queue.put(package['external_command'])


    def __submit(self,package):
        #Check if queue exists
        #if a queue with such a destination doesn't exist anymore then create a new one
        queue_name = self.__queue_name(package['destination'])
        if not self.output_queues.has_key(queue_name):
            self.output_queues[queue_name] = OutputQueue(   name=queue_name,
                                    destination=package['destination'],
                                    timeout=self.timeout,
                                    retries=self.retries,
                                    chunks=self.chunks,
                                    logger=self.logger,
                                    blockcallback=self.loop)
        #Keep track of the average data size
        self.output_queues[queue_name].avg_data_size=(self.output_queues[queue_name].avg_data_size+int(sys.getsizeof(package['external_command'])))/2
        self.output_queues[queue_name].queue.put(package['external_command'])
    def __queue_name(self,destination):
        return md5(str(destination)).hexdigest()
class OutputQueue(threading.Thread):
    def __init__(self,name=None,destination=None,timeout=None,retries=None,chunks=None,logger=None,blockcallback=None):
        threading.Thread.__init__(self)
        self.name=name
        self.type=destination['type']
        self.locations=destination['locations']
        self.username=destination.get('username',None)
        self.password=destination.get('password',None)
        self.token=destination.get('token',None)
        self.timeout=timeout
        self.retries=retries
        self.chunks=chunks
        self.logger=logger
        self.loop=blockcallback
        self.queue=Queue.Queue(0)
        self.loadbalance=LoadBalance()
        self.avg_data_size=0
        self.queue_size=0
        self.daemon=True
        self.submitlock=False
        self.submittimer=1
        self.submitmaxtimer=3600
        self.start()
    def run(self):
        self.logger.info('Delivery queue %s of type %s started with destination %s.'%(self.name,self.type,self.locations))
        while self.loop.block() == True:
            bulk = []
            while not self.queue.empty() and len(bulk) <= self.chunks:
                bulk.append(self.queue.get())
            if len(bulk) > 0 and self.submitlock != True:
                while self.__submit(    type=self.type,
                            locations=self.locations,
                            data=bulk,
                            size=len(bulk),
                            queue_size=self.queue.qsize(),
                            queue_bytes=self.get_size()
                            ) != True:
                    self.logger.info('Setting submitlock and wait for %s seconds.'%(self.submittimer))
                    self.submitlock=True
                    time.sleep(self.submittimer)
                    #increment sleeper with random timer
                    if  self.submittimer < self.submitmaxtimer:
                        self.submittimer = random.randint(self.submittimer, self.submittimer*2)
            self.submitlock=False
            self.submittimer=1
            time.sleep(0.5)
    def __submit(self,type=None,locations=None,data=None,size=None,queue_size=None,queue_bytes=None):
        location = self.loadbalance.choose(locations)
        if type == 'file':
            connector = DeliverFile(    location=location,
                            data=data,
                            size=size,
                            queue_size=queue_size,
                            queue_bytes=queue_bytes,
                            logger=self.logger)
        elif type == 'named pipe' or type == 'local' or type == 'pipe':
            connector = DeliverNamedPipe(   location=location,
                            data=data,
                            size=size,
                            queue_size=queue_size,
                            queue_bytes=queue_bytes,
                            logger=self.logger)
        elif type == 'nscaweb':
            connector = DeliverNscaweb( location=location,
                            data=data,
                            username=self.username,
                            password=self.password,
                            size=size,
                            queue_size=queue_size,
                            queue_bytes=queue_bytes,
                            logger=self.logger)
        elif type == 'nrdp':
            connector = DeliverNrdp(    location=location,
                            data=data,
                            username=self.username,
                            password=self.password,
                            token=self.token,
                            size=size,
                            queue_size=queue_size,
                            queue_bytes=queue_bytes,
                            logger=self.logger)
        connector.join(30)
        if connector.isAlive() == True:
            self.logger.error('A timeout occurred writing to location %s.'%(location))
            return False
        elif connector.status == False:
            return False
        elif connector.status == True:
            return True
    def get_size(self):
        if self.queue.qsize() != 0:
            return self.avg_data_size*self.queue.qsize()
        else:
            return 0
class DeliverFile(threading.Thread):
    def __init__(self,location=None,data=None,size=None,queue_size=None,queue_bytes='0',logger=None):
        threading.Thread.__init__(self)
        self.location=location
        self.data=data
        self.size=size
        self.queue_size=queue_size
        self.queue_bytes=queue_bytes
        self.logger=logger
        self.status=False
        self.daemon=True
        self.start()
    def run(self):
        start=time.time()
        try:
            self.location=self.location.rstrip('/')
            cmd=open(self.location,'a')
            if len(self.data) == 1:
                cmd.write(self.data[0]+'\n')
            else:
                cmd.write('\n'.join(self.data)+'\n')
            cmd.close()
            end=time.time()
            self.status=True
            self.logger.info("Data succesfully submitted to %s in %s seconds. %s commands processed. Delivery queue left %s items. Size: %s bytes"%(self.location,round(end-start,3),self.size,self.queue_size,self.queue_bytes))
        except Exception as error:
            self.status=False
            self.logger.error('Error submitting data to file %s. Reason: %s. Delivery queue left %s items. Size: %s bytes'%(self.location,error,self.queue_size,self.queue_bytes))
class DeliverNamedPipe(threading.Thread):
    def __init__(self,location=None,data=None,size=None,queue_size=None,queue_bytes='0',logger=None):
        threading.Thread.__init__(self)
        self.location=location
        self.data=data
        self.logger = logger
        self.status=False
        self.size=size
        self.queue_size=queue_size
        self.queue_bytes=queue_bytes
        self.daemon=True
        self.start()
    def run(self):
        start=time.time()
        try:
            if os.path.exists(self.location):
                mode = os.stat(self.location)[ST_MODE]
                if S_ISFIFO(mode):
                    cmd=open(self.location,'w', buffering=1)
                    if len(self.data) == 1:
                        cmd.write(self.data[0].encode('utf-8')+'\n')
                    else:
                        cmd.write(('\n'.join(self.data)+'\n').encode('utf-8'))
                    cmd.close()
                    end=time.time()
                    self.logger.info("Data succesfully submitted to %s in %s seconds. %s commands processed. Delivery queue left %s items. Size: %s bytes."%(self.location,round(end-start,3),self.size,self.queue_size,self.queue_bytes))
                    self.status=True
                else:
                    self.logger.error("%s is not a named pipe"%(self.location))
                    self.status=False
            else:
                self.logger.error("%s does not exist"%(self.location))
                self.status=False
        except Exception as error:
            self.logger.error("Error submitting data to %s. Reason: %s. Delivery queue left %s items. Size: %s bytes"%(self.location,error,self.queue_size,self.queue_bytes))
            self.status=False
class DeliverNscaweb(threading.Thread):
    def __init__(self,location=None,data=None,username=None,password=None,size=None,queue_size=None,queue_bytes='0',logger=None):
        threading.Thread.__init__(self)
        self.location=location
        self.data=data
        self.username=username
        self.password=password
        self.size=size
        self.queue_size=queue_size
        self.queue_bytes=queue_bytes
        self.logger=logger
        self.status=False
        self.opener = urllib2.build_opener()
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('User-agent', 'NSCAweb')]
        self.daemon=True
        self.start()
    def run(self):
        start=time.time()
        try:
            data = '\n'.join(self.data)
            data = data.decode("ascii", "ignore")
            nscaweb_data = urlencode({'username': self.username, 'password': self.password, 'input': data})
            conn = self.opener.open(self.location,nscaweb_data)
            conn.close()
            end=time.time()
            self.logger.info("Data succesfully submitted to %s in %s seconds. %s commands processed. Delivery queue left %s items. Size: %s bytes."%(self.location,round(end-start,3),self.size,self.queue_size,self.queue_bytes))
            self.status=True
        except Exception as error:
            self.logger.error('Error submitting data to NSCAweb %s. Reason: %s. Delivery queue left %s items. Size: %s bytes'%(self.location,error,self.queue_size,self.queue_bytes))
            self.status=False
class DeliverNrdp(threading.Thread):
    def __init__(self,location=None,data=None,username=None,password=None,token=None,size=None,queue_size=None,queue_bytes='0',logger=None):
        threading.Thread.__init__(self)
        self.location=location
        self.data=data
        self.username=username
        self.password=password
        self.token=token
        self.size=size
        self.queue_size=queue_size
        self.queue_bytes=queue_bytes
        self.logger=logger
        self.status=False
        self.opener = urllib2.build_opener()
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('User-agent', 'NSCAweb')]
        self.daemon=True
        self.start()
    def run(self):
        start=time.time()
        try:
            nrdp_data = urlencode({'token':self.token,'XMLDATA':'\n'.join(self.data),'cmd':'submitcheck','btnSubmit':'Submit Check Data'})
            conn = self.opener.open(self.location,nrdp_data)
            try:
                content = conn.read()
                conn.close()
                root = ElementTree.XML(content)

            except:
                self.logger.error('Error submitting data to NRDP %s. Reason: NRDP answer was non xml.'%(self.location))
                self.status=False
                conn.close()
                return

            if root[0].text == "-1":
                self.logger.error('Error submitting data to NRDP %s. Reason: %s.'%(self.location,root[1].text))
                self.status=False
                conn.close()
                return
            else:
                end=time.time()
                self.logger.info('Data succesfully submitted to %s in %s seconds. %s batch processed. Delivery queue left %s items. Size: %s bytes'%(self.location,round(end-start,3),"1",self.queue_size,self.queue_bytes))
                self.status=True
                conn.close()
                return
        except Exception as error:
            self.logger.error('Error submitting data to NRDP %s. Reason: %s. Delivery queue left %s items. Size: %s bytes'%(self.location,error,self.queue_size,self.queue_bytes))
            self.status=False

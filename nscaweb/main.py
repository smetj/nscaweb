#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       nscaweb
#
#       Copyright 2010 Jelle Smet <web@smetj.net>
#
#       This file is part of NSCAweb.
#
#           NSCAweb is free software: you can redistribute it and/or modify
#           it under the terms of the GNU General Public License as published by
#           the Free Software Foundation, either version 3 of the License, or
#           (at your option) any later version.
#
#           NSCAweb is distributed in the hope that it will be useful,
#           but WITHOUT ANY WARRANTY; without even the implied warranty of
#           MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#           GNU General Public License for more details.
#
#           You should have received a copy of the GNU General Public License
#           along with NSCAweb.  If not, see <http://www.gnu.org/licenses/>.

import cherrypy
import os
import sys
import time
import signal
import Queue
import threading
import daemon
import select
import logging
from nscaweb.server import ThreadControl
from nscaweb.server import ConfigFileMonitor
from nscaweb.authentication import Authenticate
from nscaweb.communication import SubmitListener

from cherrypy import log
from configobj import ConfigObj
from optparse import OptionParser
from time import gmtime
from pkg_resources import get_distribution

class WebServer(threading.Thread):
    def __init__(self, host, port, pid, ssl="off", ssl_certificate=None, ssl_private_key=None, htmlContent=None, enable_logging="1", blockcallback=None):
        threading.Thread.__init__(self)
        self.host=host
        self.port=port
        self.ssl=ssl
        self.ssl_certificate=ssl_certificate
        self.ssl_private_key=ssl_private_key
        self.htmlContent=htmlContent
        self.enable_logging=enable_logging
        self.loop=blockcallback
        self.daemon=True
        self.start()

    def run(self):
        logger.info("WebServer thread started on %s:%s"%(self.host,self.port))
        config={'global': {'server.socket_host': self.host}}
        cherrypy.config.update(
                                {
                                'global':
                                    {
                                    'server.socket_port': int(self.port),
                                    'server.socket_host': self.host,
                                    'tools.sessions.on': False,
                                    'log.screen': False
                                    }
                                }
                                )

        #check if we need to run over https or not
        if self.ssl == "on":
            cherrypy.config.update(
                                    {
                                    'server.ssl_certificate': self.ssl_certificate,
                                    'server.ssl_private_key': self.ssl_private_key
                                    }
                                  )

        cp_app = cherrypy.tree.mount(self.htmlContent,'/',config=config)

        if self.enable_logging == '1':
            cp_app.log.access_log_format = '%(h)s %(l)s %(u)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
            cp_app.log.access_log = logger
            #log.error_log = logger
            #help(log.error_log)
        cherrypy.engine.start()
        while self.loop.block() == True:
            time.sleep(0.1)
        cherrypy.engine.exit()
        logger.info("WebServer thread stopped.")

class HtmlContent():
    '''Class which provides form to accept incoming NSCAweb data.'''

    def __init__(self,queueDefinitions,submitListener,authentication):
        self.queueDefinitions=queueDefinitions
        self.submitListener=submitListener
        self.authentication=authentication

    def index(self,*args,**form):
        pass
    index.exposed = False

    def queue(self,*args,**form):
        try:
            if form.has_key('username') and form.has_key('password') and form.has_key('input'):
                if self.authentication.do(username=form['username'],password=form['password']):
                    form['input']=form['input'].rstrip()
                    if len(args)==0:
                        counter=0
                        for line in form['input'].split('\n'):
                            counter+=1
                            #Since this is the broadcast, run over all queues and dump the line in each queue
                            for name in self.queueDefinitions:
                                if self.queueDefinitions[name]['enable'] == "1":
                                    package = self.construct_package(name=name,queueDefinitions=self.queueDefinitions,line=line)
                                    try:
                                        self.submitListener.dump(package)
                                    except Exception:
                                        logger.warn("Queue size limit reached. Data purged.")
                                        continue
                        logger.info("%s items dumped into the broadcast queue for user %s from IP %s."%(counter,form['username'],cherrypy.request.remote.ip))
                    elif len(args)==1:
                        if self.queueDefinitions.has_key(args[0]) and self.queueDefinitions[args[0]]['enable'] == "1":
                            counter=0
                            for line in form['input'].split('\n'):
                                counter+=1
                                package = self.construct_package(name=args[0],queueDefinitions=self.queueDefinitions,line=line)
                                try:
                                    self.submitListener.dump(package)
                                except Exception:
                                    logger.warn("Queue %s size limit reached. Data discarted."%(args[0]))
                                    raise cherrypy.HTTPError("500 Internal Server Error", "Queue %s is full. Data discarted."%(args[0]))

                            logger.info("%s items dumped into queue %s for user %s from IP %s."%(counter,args[0],form['username'],cherrypy.request.remote.ip))
                        else:
                            logger.warn("Queue %s does not exist or is disabled. Data is purged for user %s from IP %s."%(args[0],form['username'],cherrypy.request.remote.ip))
                    else:
                        logger.warn("Malformed url for user %s from IP %s"%(form['username'],cherrypy.request.remote.ip))
                else:
                    logger.warn("Access denied for user %s from IP %s."%(form['username'],cherrypy.request.remote.ip))
            else:
                logger.warn("Incomplete data submitted from IP %s."%(cherrypy.request.remote.ip))
        except cherrypy.HTTPError as err:
            raise cherrypy.HTTPError("500 Internal Server Error", str(err[1]))
        except Exception as error:
            logger.warn("Malformed data submitted from IP %s. Maybe something wrong with the destination configuration in the config file."%(cherrypy.request.remote.ip))
    queue.exposed = True

    def default(self, *args, **kwargs):
        pass
    default.exposed = True

    def construct_package(self,name,queueDefinitions,line):
        package={'destination':{
            'type' : queueDefinitions[name]['type'],
            'locations' : queueDefinitions[name]['locations'].split(','),
            'username' : queueDefinitions[name].get('username',None),
            'password' : queueDefinitions[name].get('password',None),
            'token' : queueDefinitions[name].get('token',None)
            },
            'external_command' : line
            }
        return package

class Logger():
    '''Creates a logger class.'''

    def __init__(self,logfile='', scrlog=True, syslog='1', loglevel=logging.INFO):
        self.logfile=logfile
        self.scrlog=scrlog
        self.syslog=syslog
        self.loglevel=loglevel
        self.format=logging.Formatter(fmt='%(asctime)s %(levelname)s: %(message)s',datefmt=None)
        self.syslog_format=logging.Formatter(fmt='NSCAweb: %(message)s',datefmt=None)
        self.log = logging.getLogger(__name__)
        self.log.setLevel(self.loglevel)
        if logfile != '':
            self.file_handler = logging.FileHandler( logfile )
            self.file_handler.setFormatter(self.format)
            self.log.addHandler(self.file_handler)
        if scrlog == True:
            self.scr_handler = logging.StreamHandler()
            self.scr_handler.setFormatter(self.format)
            self.log.addHandler(self.scr_handler)
        if syslog == '1':
            from logging.handlers import SysLogHandler
            if os.path.exists('/var/run/syslog'):
                self.sys_handler = SysLogHandler(address='/var/run/syslog')
            else:
                self.sys_handler = SysLogHandler(address='/dev/log')

            self.sys_handler.setFormatter(self.syslog_format)
            self.log.addHandler(self.sys_handler)

class NamedPipe(threading.Thread):

    def __init__(self, directory, name, submitListener, queueDefinitions=None, blockcallback=None):
        threading.Thread.__init__(self)
        self.directory=directory
        self.name=name
        self.submitListener=submitListener
        self.queueDefinitions=queueDefinitions
        self.loop=blockcallback
        self.absolutePath=self.directory+'/'+self.name
        self.daemon=True
        self.start()

    def run(self):
        try:
            os.unlink ( self.absolutePath )
        except:
            pass
        try:
            os.mkfifo ( self.absolutePath )
        except Exception as err:
            logger.critical('There was an error creating the named pipe %s. Reason: %s'%(self.absolutePath,err))
            return
        else:
            logger.info('Named pipe listener created with name %s'%(self.name))
        try:
            fifo = open(self.absolutePath,'r')
            while self.loop.block() == True:
                line = fifo.readline()[:-1]
                if len(line) > 0:
                    if self.name == 'broadcast':
                        for queueDefinition in self.queueDefinitions:
                            if self.queueDefinitions[queueDefinition]['enable'] == '1':
                                package = self.construct_package(name=queueDefinition,queueDefinitions=self.queueDefinitions,line=line)
                                self.submitListener.input_queue.put(package)
                    else:
                        package = self.construct_package(name=self.name,queueDefinitions=self.queueDefinitions,line=line)
                        self.submitListener.input_queue.put(package)
                else:
                    time.sleep(0.1)
        except Exception as err:
            logger.critical('There was an error reading from the named pipe %s. Reason: %s'%(self.absolutePath,err))
            os.unlink(self.absolutePath)
            return
        try:
            fifo.close()
            os.unlink ( self.absolutePath )
        except:
            pass
        logger.info('Named pipe listener with name %s has exit.'%(self.name))
        return

    def stop(self):
        try:
            breakBlock = open (self.absolutePath,'r+')
            breakBlock.write('\n')
            breakBlock.close()
        except:
            pass

    def construct_package(self, name, queueDefinitions, line):
        package={'destination':{
            'type' : queueDefinitions[name]['type'],
            'locations' : queueDefinitions[name]['locations'].split(','),
            'username' : queueDefinitions[name].get('username',None),
            'password' : queueDefinitions[name].get('password',None),
            'token' : queueDefinitions[name].get('token',None)
            },
            'external_command' : line
            }
        return package

class Server():
    def __init__(self,configfile=None):
        self.configfile=configfile
        try:
            self.config=ConfigObj(self.configfile)
        except Exception as err:
            sys.stderr.write('There appears to be an error in your configfile:\n')
            sys.stderr.write('\t'+ str(type(err))+" "+str(err) + "\n" )
            os.kill(os.getpid(),signal.SIGKILL)
    def check_running(self):
        if (os.path.exists(self.config['application']['pidfile'])):
            pid_file = open(self.config['application']['pidfile'],'r')
            pid = pid_file.readline()
            pid_file.close()
            try:
                os.kill(int(pid),0)
            except:
                sys.stderr.write('PID file detected but no process with such a PID.  I will overwrite it.\n')
            else:
                sys.stderr.write('There is already a version of NSCAweb running with pid %s\n'%(pid))
                sys.exit(1)
    def start(self,debug=False):

        #Set logging environment
        global logger
        logger_object = Logger( logfile=self.config['logging'].get('logfile',''),
                    scrlog=debug,
                    syslog=self.config['logging'].get('enable_syslog',"0")
                    )
        logger = logger_object.log
        logger.info('started')


        #Create pid
        pidfile=open(self.config["application"]["pidfile"],'w')
        pidfile.write(str(os.getpid()))
        pidfile.close()

        #Create home for threads
        server=ThreadControl()

        #Start a ConfigFileMonitor thread
        server.threads['configfilemonitor'] = ConfigFileMonitor (file=self.configfile,
                                        logger=logger,
                                        blockcallback=server)

        #Create Authentication object
        auth = Authenticate (   auth_type='default',
                        database=server.threads['configfilemonitor'].file['authentication'],
                        logger=logger)

        #Create SubmitListener object
        server.threads['submitListener'] = SubmitListener(  quota=int(server.threads['configfilemonitor'].file['application'].get('queue_quota','0')),
                                    logger=logger,
                                    blockcallback=server)

        #Create an HtmlContent object
        htmlContent = HtmlContent ( queueDefinitions=server.threads['configfilemonitor'].file['destinations'],
                        submitListener=server.threads['submitListener'],
                        authentication = auth)

        #Start the WebServer thread
        server.threads['webserver'] = WebServer (host=server.threads['configfilemonitor'].file['application']['host'],
                            port=server.threads['configfilemonitor'].file['application']['port'],
                            pid=server.threads['configfilemonitor'].file['application']['pidfile'],
                            ssl=server.threads['configfilemonitor'].file['application']['sslengine'],
                            ssl_certificate=server.threads['configfilemonitor'].file['application']['sslcertificate'],
                            ssl_private_key=server.threads['configfilemonitor'].file['application']['sslprivatekey'],
                            htmlContent=htmlContent,
                            enable_logging=self.config['logging'].get('enable_http_logging',"0"),
                            blockcallback=server)

        #Start NamedPipe threads
        if server.threads['configfilemonitor'].file['pipes']['enable'] == "1":
            for destination in server.threads['configfilemonitor'].file['destinations']:
                if server.threads['configfilemonitor'].file['destinations'][destination]['enable'] == "1":
                    server.threads['namedPipe'+destination]  = NamedPipe(   directory=server.threads['configfilemonitor'].file['pipes']['directory'],
                                                                            name=destination,
                                                                            submitListener=server.threads['submitListener'],
                                                                            queueDefinitions=server.threads['configfilemonitor'].file['destinations'],
                                                                            blockcallback=server)

            server.threads['namedPipe'+destination]  = NamedPipe(   directory=server.threads['configfilemonitor'].file['pipes']['directory'],
                                                                    name='broadcast',
                                                                    submitListener=server.threads['submitListener'],
                                                                    queueDefinitions=server.threads['configfilemonitor'].file['destinations'],
                                                                    blockcallback=server)
        #Block here
        try:
            while server.block()==True:
                time.sleep(1)
        except KeyboardInterrupt:
            print ("Stopping all queues in a polite way. Press ctrl+c again to force stop.")
            try:
                #write bogus data into pipes
                while server.stop_all([server.threads,server.queues]) == False:
                    time.sleep(1)
                    logger.info('Waiting for all queues to end.')
            except KeyboardInterrupt:
                os.remove(server.threads['configfilemonitor'].file['application']['pidfile'])
                exit
            try:
                os.remove(server.threads['configfilemonitor'].file['application']['pidfile'])
            except:
                pass

    def stop(self):
        try:
            pidfile=open(self.config["application"]["pidfile"],'r')
            pid=pidfile.read()
            pidfile.close()
            os.kill(int(pid),signal.SIGINT)
        except Exception as error:
            sys.stderr.write('Could not stop NSCAweb.  Reason: %s\n'%error)

    def kill(self):
        try:
            pidfile=open(self.config["application"]["pidfile"],'r')
            pid=pidfile.read()
            pidfile.close()
            os.remove(self.config["application"]["pidfile"])
            os.kill(int(pid),signal.SIGKILL)
        except Exception as error:
            sys.stderr.write('Could not kill NSCAweb.  Reason: %s\n'%error)

class Help():
    def __init__(self):
        pass
    def usage(self):
        print ('NSCAweb %s Copyright 2009,2010,2011 by Jelle Smet <jelle@smetj.net>' %( get_distribution('nscaweb').version))
        print ('''Usage: nscaweb command --config configfile

    Valid commands:

        start   Starts the nscaweb daemon in the background.

        stop    Gracefully stops the nscaweb daemon running in the background.

        kill    Kills the nscaweb daemon running with the pid defined in your config file.

        debug   Starts the nscaweb daemon in the foreground while showing real time log and debug messages.
            The process can be stopped with ctrl+c which will ends NSCAweb gracefully.
            A second ctrl+c will kill NSCAweb.

    Parameters:
        --config    Defines the location of the config file to use.  The parameter is obligatory.
                -c can also be used.

NSCAweb is distributed under the Terms of the GNU General Public License Version 3. (http://www.gnu.org/licenses/gpl-3.0.html)

For more information please visit http://www.smetj.net/nscaweb/
''')
        return()

def main():

    try:
        #Parse command line options
        parser = OptionParser()
        parser.add_option("-c",  "--config", dest="configfile", default="/opt/nscaweb/etc/main.conf", type="string", help="config file")
        (commandline_options,commandline_actions)=parser.parse_args()
        server=Server(configfile=commandline_options.configfile)
        #Execute command
        if len(commandline_actions) != 1:
            Help().usage()
            sys.exit
        elif commandline_actions[0] == 'start':
            server.check_running()
            print ("Starting NSCAweb in background.")
            with daemon.DaemonContext():
                server.start()
        elif commandline_actions[0] == 'debug':
            print ("Starting NSCAweb in foreground.")
            server.check_running()
            server.start(debug=True)
        elif commandline_actions[0] == 'stop':
            print ("Stopping NSCAweb gracefully.  Tail log for progress.")
            server.stop()
        elif commandline_actions[0] == 'kill':
            print ("Killing NSCAweb forcefully.")
            server.kill()
        elif commandline_actions[0] == 'dump':
            pass
        else:
            Help().usage()
            print ('Unknown option %s \n' %(commandline_actions[0]))
            sys.exit()
    except Exception as err:
        sys.stderr.write('A fatal error has occurred.\n')
        sys.stderr.write('Please file a bug report to https://github.com/smetj/nscaweb/issues including:\n')
        sys.stderr.write('\t - NSCAweb version.\n')
        sys.stderr.write('\t - A copy of your config file.\n')
        sys.stderr.write('\t - Your OS and version.\n')
        sys.stderr.write('\t - Your Python and Cherrypy version.\n')
        sys.stderr.write('\t - The steps to take to reproduce this error.\n')
        sys.stderr.write('\t - This piece of information: '+ str(type(err))+" "+str(err) + "\n" )
        sys.exit(1)

if __name__ == '__main__':
    main()
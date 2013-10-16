NSCAweb
=======

What?
-----

NSCAweb is a Nagios core based monitoring solution addon which allows you to
easily submit (passive) host and service checks over http(s) to the Nagios
external command file. It aims to be a better,more feature rich alternative
than the classic NSCA daemon.

NSCAweb has following features:

 - http(s) as transport makes it more friendly in a firewalled environment.
 - SSL encryption when desired.
 - Supports multiline plugin & performance output.
 - Accepts data coming over http or from local named pipes.
 - Submit data to many types of destinations: named pipes (nagios.cmd), NSCAweb, NRDP or a file.
 - Loadbalance and failover between multiple urls per destination.
 - Duplicate and forward passive check results to an "unlimited" amount of destinations.
 - Submit messages to 1 destination or all destinations depending on the url messages are send to.
 - Simultaneous local and remote delivery.
 - Each destination has an independent, dedicated thread and queue.
 - Buffering of unavailable destinations and resubmitting when destination comes available to prevent data loss.
 - Builtin, multiuser authentication.
 - Trivial to submit check results using http post.
 - Submit check results in bulk or one by one.
 - Use curl as a client from the command line.

Installation
------------

You can install NSCAweb from https://pypi.python.org/pypi by executing:


    $ easy_install nscaweb


Or you can install NSCAweb directly from source when desired:

    $ git clone https://github.com/smetj/nscaweb.git
    $ cd nscaweb
    $ sudo python setup.py install


Any Python related dependencies should be resolved and installed
automatically.


Usage
-----

After installing the package you should have the `nscaweb` command available.

Starting in foreground.  Press ctrl+c to exit:

    $ nscaweb debug --config /etc/nscaweb.conf

Starting in background.

    $ nscaweb start --config /etc/nscaweb.conf

Stop a background process:

    $ nscaweb stop --config /etc/nscaweb.conf



Configuration
-------------

The configuration file is in ini style and has 4 sections:

application
~~~~~~~~~~~

.. code-block:: ini

    [ "application" ]
        host                = "0.0.0.0"
        port                = "5668"
        pidfile             = "/opt/nscaweb/var/nscaweb.pid"
        accesslogfile       = "/opt/nscaweb/var/nscaweb_access.log"
        errorlogfile        = "/opt/nscaweb/var/nscaweb_errors.log"
        sslengine           = "off"
        sslcertificate      = ""
        sslprivatekey       = ""


*   host

    The IP address NSCAweb should bind to and listen on. By default NSCAweb
    listens on all interfaces it can find on the machine. This behavior is
    reached by using the "0.0.0.0" which effectively means listen on all
    interfaces. If you want to have NSCAweb to listen on a certain ip address,
    then you can define it here. If you want NSCAweb only to listen on the
    localhost you can define "127.0.0.1".

*   port

    The port on which NSCAweb should listen. By default NSCAweb listens on port
    12345. It can be changed to what makes most sense to your environment.

*   pidfile

    The location of the pidfile. The pidfile holds the process number of the
    NSCAweb daemon when it has been started in background mode. It's not created
    when NSCAweb is started in debug mode. The pidfile is used by NSCAweb itself
    for server control. Do not delete this file while NSCAweb is running in
    background mode.

*   accesslogfile

    The location of the access logfile. This logfile contains all client requests.
    It basically has the same output as a webserver log file.

*   errorlogfile

    The location of the error logfile. This logfile contains all error and debug
    related information.

*   sslengine

    Makes NSCAweb listen to https instead of standard http and encrypt all
    traffic. The allowed values are "on" and "off". If you have defined on you
    need to define the sslcertificate and the sslprivatekey parameters. If you
    choose off, the sslcertificate and sslprivatekey parameters are ignored.

*   sslcertificate

    Defines the place of the sslcertificate. You can create and use self-signed
    certificates or an official one. You can basically follow any Apache/ssl
    certificate creation guide to create one.

*   sslprivatekey

    Defines the place of the ssl private key. When you're in the process of
    creating your certificate you will also have your private key. This is a quite
    sensitive piece of information. Make sure it's on a safe place.


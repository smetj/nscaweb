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

The application section controls the behaviour of the daemon itself.

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


settings
~~~~~~~~

The settings section allows you to control how the application behaves and
responds to requests.

.. code-block:: ini

    [ "settings" ]
        config_check_interval   = "10"
        enable_pipe_submit      = "1"
        nagios_cmd              = "/var/lib/nagios3/rw/nagios"
        queue_process_batch     = "5000"


*   config_check_interval

    Defines the value in seconds of the config check interval. This parameter
    determines how much time is there between checking if the config file has been
    changed.

*   enable_pipe_submit

    Enables or disables writing passive checks to a local Nagios External Command
    file. Valid values are 0(disable) and 1(enable).


*   nagios_cmd

    Defines the location of the Nagios external command file. This is the absolute
    filename of the Nagios external command file. Make sure the user under which
    NSCAweb is running has sufficient privileges to write.


*   queue_process_batch

    Defines the maximum amount of passive check results to submit at once.


nscaweb_definitions
~~~~~~~~~~~~~~~~~~~

The section defines additional NSCAweb destinations to which this instance has
to forward incoming passive checks. Multiple NSCAweb destinations are
possible. The amount of destinations is limited to the available resources.
All passive checks coming into NSCAweb are put into the master queue. Each
defined destination (pipe & nscaweb definitions) has its own queue to which
all messages from the master queue are copied.

.. code-block:: ini

    [ "nscaweb_definitions" ]
        [[ "main_monitoring_1" ]]
            enable          = "0"
            host            = "host_running_nscaweb_1:5668"
            username        = "default"
            password        = "changeme"
            compress_data   = "0"

        [[ "main_monitoring_2" ]]
            enable          = "0"
            host            = "host_running_nscaweb_2:5668"
            username        = "default"
            password        = "changeme"
            compress_data   = "0"

*   instance name

    Note: You can't use 'pipe' as an instance name as it's a reserved name for
    internal usage.
    In the above example the instance name is "main_monitoring_1".
    It is freely chosen, unique name identifying the NSCAweb destination. Keep the
    name informative, as it will help you identifying in the log which destination
    is not behaving well. You can create as many destinations/definitions as you
    want.

*   enable

    This parameter enables or disables the NSCAweb destination definition. Allowed
    values are 0(disable) and 1(enable).

*   host

    This parameter defines the address of the remote host running NSCAweb. You can
    use a hostname or ipaddress. The portnumber can be added using :

*   username

    The username to authenticate against the remote NSCAweb instance.

*   password

    The password to authenticate against the remote NSCAweb instance.

authentication
~~~~~~~~~~~~~~

The authentication section contains the usernames and passwords used to
authenticate to NSCAweb in order to dump data.

.. code-block:: ini

    [ "authentication" ]
            default         = "6ac371cc3dc9d38cf33e5c146617df75"


This is a simple section which contains a list of username and encrypted
password pairs. In this case there's only 1 user defined with the login name
"default" and password "changeme".

The password is encrypted as an md5sum.  To generate a hash value out of a
string you can execute the following:

    $ echo changeme|md5sum 

The authentication happens by submitting a login and password form field. You
must have at least 1 entry here.

Warning: Each NSCAweb installation comes with the default username "default"
and password "changeme". CHANGE IT!.

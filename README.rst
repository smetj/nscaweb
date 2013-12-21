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


Support
-------

Post a message in Google groups: https://groups.google.com/forum/#!forum/nscaweb

Submit bugreports to: https://github.com/smetj/nscaweb/issues


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
        sslengine           = "off"
        sslcertificate      = ""
        sslprivatekey       = ""
        queue_quota         = "104857600"


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

*   queue_quota

    The value in bytes a queue is allowed to contain before refusing data.

logging
~~~~~~~

Logging related options

.. code-block:: ini

    [ "logging" ]
        logfile             = "/var/log/nagios/nscaweb.log"
        enable_syslog       = "1"
        enable_http_logging = "0"

*   logfile

    The location of the logfile.  If commented, no logfile is created.

*   enable_syslog

    If enabled, writes logs to syslog.

*   enable_http_logging

    If enabled, includes any http request related logging to the log destination.

pipes
~~~~~

NSCAweb can accept data over named pipe.

.. code-block:: ini

    [ "pipes" ]
        enable          = "1"
        directory       = "/var/tmp/"

*   enable

    When enabled, creates the named pipes.

*   directory

    The location of the named pipes.


For each defined destination a corresponding named pipe is created.
Submitting data to a named pipe results in that data being send to the
corresponding destination. A special "broadcast" named pipe is also created
which submits incoming data to all defined destinations.

destinations
~~~~~~~~~~~~

The section defines additional NSCAweb destinations to which this instance has
to forward incoming passive checks. Multiple NSCAweb destinations are
possible. The amount of destinations is limited to the available resources.
All passive checks coming into NSCAweb are put into the master queue. Each
defined destination (pipe & nscaweb definitions) has its own queue to which
all messages from the master queue are copied.

.. code-block:: ini

    [ "destinations" ]

        [[ "local" ]]
            enable      = "0"
            type        = "local"
            locations   = "/opt/nagios/var/rw/nagios.cmd"

        [[ "master" ]]
            enable      = "0"
            type        = "nscaweb"
            locations   = "http://prod-ctrl-nagios-001.almere.tomtom.com:15668/queue/local"
            username    = "default"
            password    = "changeme"

        [[ "nagiosWithNrdp" ]]
            enable      = "0"
            type        = "nrdp"
            locations   = "http://nagios/nrdp/"
            username    = "default"
            password    = "changeme"
            token       = "mysecrettoken"

        [[ "debugging" ]]
            enable      = "0"
            type        = "file"
            locations   = "/tmp/external_commands.log"

Each destination should have a unique name.  The name identifies the
destination when submitting data.  A destination name is free to choose.  In
the above example we have defined names: local, master, nagiosWithNrdp and
debugging.

*   enable

    This parameter enables or disables the NSCAweb destination definition. Allowed
    values are 0(disable) and 1(enable).

*   type

    The type of destination.  There are 4 types:

    - nscaweb
    - nrpd
    - local
    - file

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

**Warning**: Each NSCAweb installation comes with the default username "default"
and password "changeme". CHANGE IT!.


Transport data with NSCAweb
---------------------------

A typical NSCAweb setup looks like this:

.. image:: docs/nscaweb.png

NSCAweb has for each defined destination

From command line to NSCAweb
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes you have to submit a check result (or other command) into Nagios
from a remote host.  You can do that by simply using curl or wget from command
line.  In the above diagram, we have server_3 sending check updates to
server_4.  Server_4 then writes the incoming check results into the Nagios
external command pipe.



Following example command does that:

    printf "[%lu] PROCESS_SERVICE_CHECK_RESULT;localhost;True 1;2;CRITICAL- Whatever\n" $(date +%s) | \
    curl -d username="default" -d password="changeme" --data-urlencode input=@- http://localhost:5668/queue

From NSCAweb to NSCAweb
~~~~~~~~~~~~~~~~~~~~~~~

NSCAweb is a http based daemon which receives data over http post requests. It
accepts data just like your browser posts and requests data to a webserver. In
order to interact with NSCAweb you need an http client such as wget, curl,
libwww, ...

There are 3 form fields available:

* username
* password
* input

The input field should contain 1 or more entries with the same syntax as
described below. When you use multiple lines as plugin output then use "\\\n"
to separate those multiple lines. NSCAweb will consider each "\n" as a new
Nagios external command.

**Warning**: Keep in mind that all data you send to NSCAweb needs to be URL
encoded. Submit 1 check result to NSCAweb using curl.

**Warning**: Make sure to use a version of curl which supports the '--data-
urlencode' parameter.

Now lets dump the result for 1 service check into it using curl:

    $ now=$(date +%s)

    $ data=$(printf "[%lu] PROCESS_SERVICE_CHECK_RESULT;localhost;True 1;2;CRITICAL- Whatever\n" $now)

    $ curl -d username="default" -d password="changeme" --data-urlencode input="$data" localhost:5668


From Nagios
~~~~~~~~~~~

When sending check results from Nagios


Submit 500 check results at once to NSCAweb using curl
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say I have 500 check results I want to dump in 1 go.

Consider following file:

    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 1;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 2;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 3;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 4;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 5;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 6;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 7;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 8;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 9;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 10;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 11;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 12;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 13;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 14;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 15;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 16;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 17;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 18;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;
    ...snip...
    [1269803591] PROCESS_SERVICE_CHECK_RESULT;localhost;True 500;2;CRITICAL- Submitted through nscaweb\nA second line of data\nAnd a third one|'perf1'=12;;;; 'perf2'=15;;;;


Execute:

    $ curl -d username="default" -d password="changeme" --data-urlencode input="$(cat /tmp/test_result_file.txt) localhost:5668


**Just make sure that the \n in between the multiline output is literally send over the NSCAweb.**
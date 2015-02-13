Directions for Deploying Solr for Open Context
=======================


PART 1. SETTING UP SOLR
------------------------------------------

(1.1) Configuring Solr:

Solr deployment is generally simple. In this example, we'll assume that you have 
downloaded Apache Solr 4.10.3 and have unpacked it in a directory called "solr". 
First, copy the "/solr/example" directory and name it "open-context". So you have
a structure like:

    /solr
        + /example
        |
        + /open-context

One you do this, copy the following file from this Git repository and put it
here:

     /solr/open-context/solr/collection1/conf

You'll be replacing the default schema.xml document with the one from this Git
repository that has the schema defined for use with Open Context. The structure
should look like this:

    /solr
        + /example
        |
        + /open-context
                      +/solr
                           +/collection1
                                       +/conf
                                            + schema.xml


(1.2) Solr User Permissions:

Some Solr deployment problems center on user permissions. Here are some handy
commands to help get Solr working. The following create a unix-user and a 
group for Solr:

     sudo adduser solr --no-create-home --disabled-login --disabled-password
     sudo groupadd solr

You can then make solr the owner of the directory where it runs and manages
its index. It will need appropriate permissions to read and write files in
this directory and sub-directories:

     sudo chown -R solr:solr /solr

You may need to fiddle some more with spcific permissions.



PART 2. KEEPING SOLR ALIVE
------------------------------------------

(2.1) Setting up a Solr restart scipt:

Open Context's use of Solr is very, very, memory intensive. The index is big,
elaborate, and requires a machine with lots of memory. In the future, our
development efforts will do more to distribute this with shards or other
strategies, but for now, our main memory management strategy is simple -
throw more memory at Solr.

However, because our use of Solr consumes so much memory, Solr can sometimes
crash. Daniel Pett (@portableant) with the Portable Antiquities Scheme kindly
shared a good tip on keeping Solr alive using a shell-script and a cronjob.
In our implementation, the shell script looks like this:

    #!/bin/bash
    PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
      
    response=$(curl -s -I -L 'http://localhost:8983/solr/admin/ping?echoParams=none&omitHeader=on' | grep HTTP); 
    status=${response#* }; # Strip off characters up to the first space
    status=${status:0:3}; # Just use the 3 digit status code
    if [ "$status" != "200" ]
        then
        cd /solr/open-context
        killall -9 java
        rm nohup.out
        nohup java -Xms500m -Xmx5000M -jar start.jar &
        echo "Solr server restarted";
    fi

Note! Be sure the code above uses the correct port for Solr! The above shell-script code is 
saved in a file called "solr-check.sh". You can check to make sure it works with:

    sudo bash solr-check.sh

The script above basically "pings" Solr. If Solr does not respond with a HTTP-200
code response, then the script kills all Java processes (note: you may want a
different restart strategy if you plan on deploying on a machine running other
Java processes!), deletes the nohup.out file (which basically daemonizes Solr),
and then starts Solr again as a daemonized process. Obviously edit this to 
work in your own production environment.


(2.1) Setting up a Check and Restart Cronjob (Automated):

Once you've checked to see that the "solr-check.sh" shell script works, you are
ready to add it as a periodic task for your server. To do so, edit your
"crontab" with the following command:

    sudo crontab -e

This will open a text editor where you can add instructions to periodically
run the "solr-check.sh" script. In the following example, I have it checking
Solr (and restarting if there's a problem) every minute:

    SHELL=/bin/sh
    PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
    * * * * * /bin/bash /path/to/your/solr-check.sh


PART 3. USING NGINX AS A PROXY FOR SOLR
------------------------------------------

(3.1) Rationale:

Applications (like Open Context) connect to Solr through HTTP requests. By default,
these requests use port 8983. However, after several perplexing hours, some deployment
contexts won't respond to outside requests made to port 8983. For instance, the Google 
Cloud seems to block or otherwise stop outide requests using that port. A port issue
may be the source of problems if you seem to get Solr started (without error messages) 
but can't get a response from Solr when you use your browser to request:

    http://your-server-domain-or-ip-address:8983/solr

One can configure Solr to use other ports, but it may make sense to use a proxy. 
Using Nginx can make certain configuration easier.

(3.2) Download and Install Nginx:

To use Nginx as a proxy, first download and install it.

   sudo apt-get install nginx

Once you've got it successfully installed. Start it up with:

     sudo /etc/init.d/nginx restart

Then you can check the unix userid for nginx:

     ps aux | grep nginx

Often Nginx will have a userid like "www-data". Getting the userid for Nginx is useful since 
it helps you set permissions for logging, etc.


(3.3) Configure Nginx as a Solr Proxy:

Below is an example Nginx configuration file for acting as a proxy to Solr. In this example, 
HTTP requests to port 80 are directed to Solr. There are no security limits on this so
absolutely NO NOT USE THIS CONFIGURATION IN PRODUCTION. It's mainly provided as a guide
to help you get started with deployment:

    server {
        # To avoid Google Cloud issues
        # with port 8983, listen
        # for requests on the HTTP
        # default port.
        listen 80;
        server_name localhost;
        error_log /opt/solr/n_error.log;
        # access_log /opt/solr/n_access.log;
        proxy_read_timeout 3600;
        proxy_buffering off;
 
        location / {
                proxy_pass http://localhost:8983;
        }
    }

Note how the "proxy_read_timeout" is set to 3600 seconds. That's a long time, but useful for executing
commands with Solr that take lots of time, like "optimize" a big index. Save the above file 
as "solr_nginx.conf". Next you need to make a symbolic link so Nginx can find it and use it:

    sudo ln -s /path/to/your/solr_nginx.conf /etc/nginx/sites-enabled/solr_nginx.conf

Sometimes there's a "default" directory in "/etc/nginx/sites-enabled". This may mess things up, and if so, 
you may want to move or delete it. Once the symbolic link is in place, start Nginx!

    sudo /etc/init.d/nginx restart

If all goes well, you should be able to connect to solr through your proxy.

Besides helping with port issues, a Nginx proxy will make it very easy to limit who
can make requests to Solr. We don't want anyone to have access to Solr's administative
console, so blocking all but a few select IP address will be an important security
consideration. I'll update this example configuration with IP address limits in the
future.

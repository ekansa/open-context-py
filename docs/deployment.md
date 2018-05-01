DEPLOYMENT INSTRUCTIONS
=======================

Setup and configuration is not the easiest thing in the world, especially for people new to Django.

This document provides some tips and methods to get past deployment issues encountered for Open Context.

These installation instructions center on deploying the application on a Debian Linux server in a Python virtual environment. The virtual environment needs to use a Python 3+ interpreter. The assumption here is that you've got super-user permissions on your server.


PART 1: REQUIRED LIBRARIES / INSTALLATIONS
------------------------------------------

(1.1) Operating system etc. updating:

It's probably a good idea to start by making sure everything is up-to-date:

    sudo apt-get update


(1.2) Python 3 Installation:

Make sure your server has all the needed Python installations. First, you'll Python 3 installed. To do so, run the following command:

    sudo apt-get install python3

This will install Python 3. It also seems best to install python-dev for both Python 2+ and Python 3. For some reason, it seems you need python-dev for both of these versions of Python in order to get Scipy to install. Here are some instructions:

    sudo apt-get install python-dev
    sudo apt-get install python3-dev


(1.3) Install pip for Python:

Pip makes it easier to install Python libraries

    python get-pip.py


(1.4) Install virtualenv for Python:

    pip install virtualenv


(1.5) Make a virtual environment for Open Context:

Navigate over to a directory where you want to install this application. Then create a virtual environment there, using the Python 3 interpreter as so:

    sudo virtualenv -p /usr/bin/python3.X oc-venv

Note to look out for permissions in this directory. It can be a “gotcha” in deployment, since some deployment approaches need to read, write, and execute permissions for software “users” that interact with Open Context and intermediary applications.

If successful, then you've got a virtual environment ready!



(1.6) Install Postgres (10+ or at least 9.4):

This is a bit more involved, since currently, package installers for many Linux machines seem to default to installing Postgres 9.1 or 9.2. Follow the instructions on the Postgres website for installation of Postgres 9.4:

    http://www.postgresql.org/download/linux/debian/

Be sure to have a Postgres user associated with your database. Be sure to also set the UNIX password for the postgres user (!) otherwise, you will have a very frustrating time (take my word for it) trying to configure Postgres, especially if you need to do something "fancy" like use a non-default location for Postgres to store data.

There can be some hassle in using another drive with Postgres to store your database. With Google Cloud look at:

    https://cloud.google.com/compute/docs/disks

First, mount your drive onto your instance. Then make sure the postgres UNIX-user has permissions on that mounted drive location. Once you do that then switch UNIX users to postgres with:

    su postgres

If you've been good, you should be able to enter the password you set for postgres. Otherwise you'll need to do that. Then change the location for postgres to store data:

    sudo /usr/lib/postgresql/9.4/bin/initdb -D /mnt/oc-data/postgresdata

More information at:
    http://www.whiteboardcoder.com/2012/04/change-postgres-datadirectory-folder.html

If that doesn't work, then you'll need to edit a configuration file. But, BEFORE YOU EDIT!! STOP POSTGRES!

    sudo /etc/init.d/postgresql stop

Once stopped, you'll find the configuration file in a location like:

    /etc/postgresql/9.4/main/postgresql.conf

Change the PGDATA directory to the directory you established for the data, with all the proper permissions added for postgre. If you don't have the permissions, you won't be able to restart Postgres with:

    sudo /etc/init.d/postgresql restart

Last, there's a library to install so the Django application can interact with the Postgres database. Install this to be able to install the psycopg2 Python library:

    sudo apt-get install libpq-dev



(1.7) Install Libraries needed for Scipy:

Numpy and Scipy are a very big, complicated libraries for scientific computing used by Open Context for some geospatial metadata summaries. It needs some installations before you can add it to your virtual environment. Install the LAPACK and BLAS libraries to the server.  Numpy and Scipy installation are likely to be the biggest configuration hurdle you'll encounter in installing the different Python libraries required for Open Context.

    sudo apt-get install liblapack-dev
    sudo apt-get install libblas-dev

You may also have to install a fortran(!) interpreter.
    sudo apt-get install gfortran

Here are some useful instructions:
    http://blog.abhinav.ca/blog/2013/09/19/pip-install-scipy-on-ubuntu/


(1.8) Install Python Libraries in your Virtual Environment:

Now you should now be able to install all of the libraries needed for this application into a virtual environment. First navigate into your virtual environment and then activate it:

    source bin/activate

Once the virtual environment is active, start by installing pip to your virtual environment:

    python get-pip.py

If pip fails to install a library, try easy_install. If that fails, there are probably dependencies (above) that you didn't install yet. Then you can install all of the Python libraries in the requirements.txt file. This will take some time, especially with Numpy and Scipy.


(1.9) Installing Open Context with Git:

You may want to install Git version control to make it easier to keep Open Context up-to-date. Here's how to install and use Git to deploy Open Context. First, install Git:

    sudo apt-get install git

Then clone Open Context from the GitHub repository for the project's production branch (recommended):

    git clone -b production https://github.com/ekansa/open-context-py.git

Once you've used Git to clone Open Context, there are settings you need to provide. Edit "change-secrets.json" to be "secrets.json", and add the correct database passwords and other settings for your instance. VERY IMPORTANT! In "secrets.json", change the "DEBUG" value to 0 so the application does not run in DEBUG mode. DEBUG mode is not safe for public exposure, since it reveals lots of details about how your site works. Look at the Django documentation for generating a Django secret key to include in “secrets.json”.

You'll need to set a full path in "secrets.json" to the open-context-py/static directory. That directory contains javascript, css, and some media files. It seemed the easiest solution to deployment headaches, so that's the way it is now. Perhaps future versions will be more self-configuring.

Also, here are some handy git commands to execute (assuming you are navigated into your project repository) to update your local instance of Open Context with what is on GitHub:

    git fetch origin
    git reset --hard origin
    git pull


(1.20) Enable Database Caching:

Open Context uses Django's caching system to temporarily store views of different resources (records, search results, etc.). This makes Open Context faster when deployed on the open Web. The specific caching method adopted by Open Context uses Django's database caching method (see: https://docs.djangoproject.com/en/1.8/topics/cache/). Once you have Open Context and its Postgres database installed, you'll need to set up database caching with the following command after navigating to the directory containing Open Context's Django "manage.py" file:

     python manage.py createcachetable


(1.21) Install Redis (In-memory Caching):

Open Context uses Django's caching system to also temporarily store some database query results and other objects. Caching reduces the number of database transactions, especially for looking up metadata about certain entities in the search / browse features. Open Context is configured to use Redis (http://redis.io/) for in-memory caching. To install Redis, see: http://redis.io/download

     wget http://download.redis.io/releases/redis-3.0.7.tar.gz
     tar xzf redis-3.0.7.tar.gz
     sudo mv redis-3.0.7 /etc/redis
     cd /etc/redis
     sudo apt-get install make
     sudo apt-get install gcc
     sudo aptitude install build-essential
     sudo make

Once you have Redis installed, you can restart it (as a daeomonized process) as follows:

     /etc/redis/src/redis-cli shutdown
     /etc/redis/src/redis-server --daemonize yes
     /etc/redis/src/redis-cli ping 'Redis ping response OK!'

If all goes well, Redis will respond to the ping request.

(1.22) Open Context via a Python Shell

You can check on things and interact with the Open Context Django application directly through the Python shell. To do so, (assuming you've already activated your virtual environment), navigate into the directory with 'manage.py' and type:

     python manage.py shell


PART 2: WEB-SERVER CONFIGURATION
--------------------------------
Once you have the production source code in place, you're ready for the real fun (FUN!) of configuring this Django application to actually work on the Web. The following description centers on using uWSGI and Nginx. Though lots of Websites claim it's easy to deploy a Django application with uWSGI and Nginx, I (a novice) found it to be a confusing configuration nightmare. So, it's probably well worth sharing how I actually (finally) got this to work on a production website.

(2.1) Installing uWSGI:

You'll need to get uWSGI to work. uWSGI acts between the Django application and the Web server, linking requests from the server to the Django application. Configuring and trouble shooting uWSGI can be a major, major, major pain in the next for a novice. To install uWSGI, first install some libraries:

    sudo apt-get install libpcre3 libpcre3-dev

Then navigate to your virtual environment, activate it:

    source bin/activate

Now you can install the Python library for uWSGI:

    pip install uwsgi

With that in place you've got an “interesting” challenge playing with the wsgi.py file in the Open Context Django app and various configuration settings with uwsgi. The open-context-py/opencontext_py/wsgi.py file has commented out code that seems useful on Linux servers. If you're having trouble getting uwsgi to work with the Open Context Django app, try using the commented out code.


(2.2) Installing Nginx and Permissions Settings:

One of the big headaches with configuration centers on read/write/execute permissions for Nginx and uWSGI for the UNIX socket that uWSGI makes for the Django application as the "upstream" source for Nginx. First of all, install the Nginx Web server if it's not already on your system:

     sudo apt-get install nginx

Once you've got it successfully installed. Start it up with:

     sudo /etc/init.d/nginx restart

Then you can check the unix userid for nginx:

     ps aux | grep nginx

Often Nginx will have a userid like "www-data". Getting the userid for Nginx is useful since it helps you set values for your uwsgi file.



(2.3) Adding a uWSGI UNIX User:

Next we'll need to create a unix user for uWSGI so it can interact with the Nginx web server. This assumes that your Nginx server has a userid of "www-data". To do so:

     sudo adduser uwsgi --no-create-home --disabled-login --disabled-password
     sudo groupadd www-data
     sudo usermod -a -G www-data uwsgi

If you run onto permissions troubles, you make also want to add the Nginx userid to the "www-data" group. That way you can set group level permissions for read/write/execute.

     sudo adduser www-data --no-create-home --disabled-login --disabled-password
     sudo usermod -a -G www-data www-data


(2.4) Activating uWSGI with a Sample Configuration File:

uWSGI can be configured in a million ways, but this describes a simple configuration to get started. We'll assume that you're putting Open Context as a sub-directory inside your virtual environment. Save the final configuration as "oc.ini":

     [uwsgi]
     home=/path/your-virtual-env
     virtualenv=/path/your-virtual-env
     chdir=/path/your-virtual-env/open-context-py
     module=opencontext_py.wsgi:application
     env=DJANGO_SETTINGS_MODULE=settings
     uid=www-data
     gid=www-data
     master=true
     vacuum=true
     socket=/path/your-virtual-env/web/%n.sock
     chmod-socket=666
     pidfile=/path/your-virtual-env/web/%n.pid
     no-site=true
     daemonize=/path/your-virtual-env/web/%n.log
     die-on-term = true
     vhost=true

This particular configuration seems to work on 2 different machines so far. So it seems it can't be too wrong. To start uwsgi, make sure you've activated your virtual environment then:

```
uwsgi --http-socket :8080 --ini /path/your-virtual-env/web/oc.ini
```

The above starts a unix socket for servers (Nginx in our case) to use in passing HTTP requests from the outside world to the Open Context Django application. Note that the socket opperates on port 8080 in this case. Choose something that won't interfere with port 80 for outside Web requests. If all goes well, you will not see an error in the log (see the path in the "daemonize" parameter above). Use the log to help debug further, since problems with the Django app sometimes appear there. If you get uWSGI to work without error, congrats! That seems to be the hardest part.


(2.5) Activating Nginx with a Sample Configuration File:

Once you got uWSGI to work without error, you can set the configuration for Nginx. Here's a sample starter configuration that seems to work for us:

```
upstream django {
   server unix:///path/your-virtual-env/web/oc.sock;
}

server {
    listen  80;
    server_name localhost;
    charset utf-8;
    access_log /path/your-virtual-env/web/nginx_access.log;
    error_log /path/your-virtual-env/web/nginx_error.log;

    location  /static/ {
       autoindex on;
       alias  /path/your-virtual-env/open-context-py/static/;
    }

    location / {
        try_files $uri @django;
    }

    location @django {
       uwsgi_pass django;
       include uwsgi_params;
    }
}
```

You can save that file as something like "oc-nginx.conf" and leave it conveniently located in the "/path/your-virtual-env/web" directory with the other Web related configurations. Next you need to make a symbolic link so Nginx can find it and use it:

    sudo ln -s /path/your-virtual-env/web/oc_nginx.conf /etc/nginx/sites-enabled/oc_nginx.conf

Sometimes there's a "default" directory in "/etc/nginx/sites-enabled". This may mess things up, and if so, you may want to move or delete it. Once the symbolic link is in place, start Nginx!

    sudo /etc/init.d/nginx restart

If all goes well, you should be able to make Web requests to a working Open Context site. If not, then hopefully these directions will at least save a few of the many possible hours you can spend on painful configuration trouble shooting!

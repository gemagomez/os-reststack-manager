This project implements a REST API that can be used to provide
completely isolated OpenStack tenants for testing purposes.

This API is fully compatible with the Jenkins plugin RESTStack (https://github.com/bwalex/reststack-jenkins-plugin.git).

This project has been tested whilst running on Ubuntu Trusty and with OpenStack Kilo as the provider of test environments.

# How to use

## Installing dependencies

This service uses venvironment to manage the dependencies. This means virtualenv
needs to be installed:

    sudo apt-get install virtualenv

Then create a virtual environment to install dependencies:

    cd os-reststack-manager
    virtualenv env

Source the environment:

    source env/bin/activate

Any other pip package required can be installed from: requirements.txt

    sudo pip install -r requirements.txt

## Running the service

Source the environment:

    source env/bin/activate

The tenant_manager can be started as follows:

    ./run.sh

The basic configuration can be found at config.py.

## Generate password file

To avoid having to store the password of the tenants in case of troubleshooting
of the test environment, the tenant's password is generated based on a password.key
file that has to be generated manually and placed in the base folder (or configure a
new location in config.py, PASSWORD_KEY).

This file can be generated as follows:

    dd if=/dev/random of=password.key bs=64 count=1

## Basic configuration

config.py contains the basic configuration of the service:

### Debug

 * DEBUG_LEVEL: Numerical value that defines the level of debug to be used:
   * CRITICAL 50
   * ERROR 40
   * WARNING 30
   * INFO 20
   * DEBUG 10
   * NOTSET 0

 * DEBUG_FORMAT: Defines the format that the debug messages will have. Example:

```
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
```

* DEBUG_DATEFMT: Defines the format of the date/time in the debug messages. Example:

```
    '%m-%d %H:%M:%S'
```

 * DEBUG_FILENAME: Full path to the debug file (comment out the creation of the log if necessary)

### VM Status DB
 * SQLALCHEMY_DATABASE_URI: URI for the SQLALCHEMY database.
 * SQLALCHEMY_TRACK_MODIFICATIONS: This setting is enabled to avoid using deprecated functionality.
 * DATABASE_CONNECT_OPTIONS: Connect options for the database.

### API IP and PORT
 * BIND_IP: IP to bind to.
 * PORT: Port to bind to.

### Cloud configuration
 * PASSWORD_KEY: This file will be used to store salt for password generation for tenants. Deterministic password generation removes the need to store passwords.
 * CREDENTIALS: This file contains the admin credentials for the cloud, see example file config/credentials.yml.sample.
 * MACHINE: This file contains the cloud init default settings, flavour name for the tenants and the phone_home_url configuration (this has to be accessible from the tenant's VM and have the API running on it). When a VM for a tenant has been deployed it will connect to the API to report that it is ready to be used.
 *NOTE*: This setting can be overriden from outside by passing a different machine config with the API call.
 * CLOUD_CONFIG: This file has information about any extra scripts that are to be run after cloud_init.
   * templates: this directory contains template/script that can be run after cloud_init finishes the installation to add any extra configuration.

## Authorised Keys

To be able to use this service, clients will have to use an Authorised token.
These tokens are generated based on a secret that is specified in the credentials
configuration file.

To generate a password a small tool is provided:

    ./gen-token.py <user name> <credentials file>

To validate manually if a token is authorised (will work) and who it belongs to:

    ./decode-token.py <token> <credentials file>


## Dependencies

The packages this project depends on are:

```
  python-flask
  python-yaml
  python-jinja2
  python-neutronclient
  python-novaclient
  python-keystoneclient
  python-glanceclient
```

## Database
The database configuration is located in config.py.


# The API

The API provides the following services:

  All actionable requests must include an authorisation token (X-Auth-Token) with a valid key.

### /tenant [POST]

   Request to creates a tenant and a bastion for jenkins to be able to use.
   This call will return whilst the tenant is being created.
   Once the tenant has finished provisioning and is ready to be used by jenkins,
   cloudinit will "phone_home" and make a call to /tenant/provisioned/<machine_id>
   when it is done.
   See app/templates/init_cloud.jinja2 for an example on how to configure the phone_home
   feature.

   Acceptable requests: application/json

   Request format:
```
     {
 	"tenant": "john",
	"pub_key": lp:~<id> or
		   <pub_key>,
	"image_id": image id or regexp ("trusty.*amd64"),
	"machine_conf": (see config/machine.yml.sample),
	"cloud_conf": (see config/cloud_conf.yml.sample)
     }
```
   In the absence of machine_conf  or cloud_conf, the local config files will be used.

   Responses:
   * 201: Created. The request was successful and the resource is being created.
   * 400: Bad Request. Caller provided invalid arguments.
   * 401: Unauthorized. Caller did not supply appropriat credentials.

### /tenant/{id} [GET]

  Retrieves the public ip of a tenant id and its status (BUILDING/READY).
  Jenkins plugin will continue to query this until the tenant is ready.
  This is call that does not require authentication.

  Response format:
```
  {
    "tenant_name" : <tenant_name>,
    "machine_id": <machine_id>,
    "ip": <tenant_ip>,
    "status": <BUILDING/READY>
  }, 200
```

  Response:
  * json,200: OK

### /tenant/{tenant_name} [DELETE]

  Deletes tenant and all the constructs associated with it.

  Response:
  * 200: Deleted.
  * 401: Unauthorized. Caller did not supply appropriat credentials.

### /tenant/provisioned/<machine_id> [POST]
  Cloudinit will "phone_home" to this URL whenever the tenant has finished
  provisioning and importing keys.

  Response:
  * 200: OK


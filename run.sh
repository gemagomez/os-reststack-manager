#!/bin/bash

set -ex

gunicorn os_reststack_manager.app:application

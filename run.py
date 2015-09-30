#!/usr/bin/env python

import config as CONF
from app import app

app.run(host=CONF.BIND_IP, port=CONF.PORT, debug=CONF.DEBUG_LEVEL)

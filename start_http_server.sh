#!/bin/bash

#python -m http.server

export FLASK_ENV=development
export FLASK_APP=flask_server
PYTHONPATH=".;../gfxdisp_python/" flask run

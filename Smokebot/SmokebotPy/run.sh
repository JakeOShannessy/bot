#!/bin/bash

xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x24 -ac +extension GLX +render -noreset" ./run.py

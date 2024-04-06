#!/bin/bash
# This scripts defines revisions and tags for a bundle.
# It is run by other BUILD scripts to define the environment.
# ----------------------------
# repo environment variables

# BOT-6.9.0-139-g65e97ad01
export BUNDLE_BOT_REVISION=65e97ad01
export BUNDLE_BOT_TAG=BOT-6.9.1

# CAD-6.9.0-0-gc5fd24b
export BUNDLE_CAD_REVISION=c5fd24b
export BUNDLE_CAD_TAG=CAD-6.9.1

# EXP-6.9.0-2-g3c0202a3c
export BUNDLE_EXP_REVISION=3c0202a3c
export BUNDLE_EXP_TAG=EXP-6.9.1

# FDS-6.9.0-92-g9743202c5
export BUNDLE_FDS_REVISION=9743202c5
export BUNDLE_FDS_TAG=FDS-6.9.1

# FIG-6.9.0-45-g5bdc65d
export BUNDLE_FIG_REVISION=5bdc65d
export BUNDLE_FIG_TAG=FIG-6.9.1

# OUT-6.9.0-0-g6b7ac2e39
export BUNDLE_OUT_REVISION=6b7ac2e39
export BUNDLE_OUT_TAG=OUT-6.9.1

# SMV-6.9.0-116-gf11dfead9
export BUNDLE_SMV_REVISION=f11dfead9
export BUNDLE_SMV_TAG=SMV-6.9.1

# ----------------------------
# github environment variables

export GH_REPO=test_bundles
export GH_FDS_TAG=BUNDLE_TEST
export GH_SMOKEVIEW_TAG=BUNDLE_TEST

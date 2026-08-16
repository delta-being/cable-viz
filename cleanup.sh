#!/bin/bash

autoflake -i --remove-all-unused-imports src/cableviz/*.py
isort src/cableviz/*py
black src/cableviz/*.py

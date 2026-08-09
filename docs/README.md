# cable-viz

## Summary
cable-viz is a program for generating cable harness drawings from YAML input. It was forked from WireViz on 9th of August 2026.

## Why cable-viz?
WireViz is an awesome tool but it's missing some features that would be really useful in my day-to-day work, and development seems to have slowed on the project. I'm keen to make some changes, so I thought I'd make it public and see if anyone else would like to join in.

## Project goals
My goals for this project are currently driven by my own work requirements, and will include (in no particular order):
- Tolerance information for wire and cable lengths
- PDF output
- Drawing frames on PDF output
- Support for displaying terminal types within connectors
- Support for conduits
- Wire/cable cut list

If I or others find the time, I would also like to make the tool more user friendly - possibly by adding a GUI.

## Project milestones
- Version 0.1 - As forked from WireViz, with name changed and at least one of the above goals met
- Version 0.2...9 - Gradually meeting all of the above goals
- Version 1.0 - Begin work on a more user-friendly version with GUI - maybe package it for Debian?
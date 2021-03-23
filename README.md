# Kodi Stash Addon

[![Build Kodi Addon](https://github.com/kodi-stash/kodi-stash-addon/actions/workflows/build.yaml/badge.svg)](https://github.com/kodi-stash/kodi-stash-addon/actions/workflows/build.yaml)

This addon for Kodi lets you browse your [Stash](https://stashapp.cc/) library, watch scenes, and view gallery pictures,
all on the big screen!

**Compatible With**: Kodi 19 "Matrix". Other versions untested.

![screenshot](screenshot.jpg)

## Features

- Navigate through your Stash library from multiple facets:
  _Scenes_, _Movies_, _Performers_, _Galleries_, and _Tags_ (_Studios_ and _Markers_ coming soon!).
  
  For _Scenes_, you can play from the beginning, play from a _Marker_, or browse to the associated
  _Galleries_, _Performers_ and _Tags_.
  
  For _Movies_, you can browse to the associated _Scenes_.

  For _Performers_, you can browse to the associated _Scenes_ and _Galleries_.

  For _Galleries_, you can view the images or browse to the associated _Scenes_ and _Performers_.
  
- Playback of all Kodi-supported video formats -- no transcode required.

- Scene fanart is randomly selected from associated Galleries (if any).

- Optionally only display _Organized_ content.

## Installation

Custom repository coming soon.

1. Download the latest release Zip file from the [Releases](https://github.com/kodi-stash/kodi-stash-addon/releases) page.
1. Move the downloaded Zip file to somewhere accessible by Kodi (e.g., the home directory of the user running Kodi).
1. Within Kodi, navigate to _Addons_ › _Install from zip file_,
   then within the file browser dialog, browse to the directory where you moved the Zip file and select the downloaded file.
1. _Kodi Stash Addon_ is now installed.

By default _Kodi Stash Addon_ uses `http://localhost:9999` as the Stash server address to connect to.
Unless Stash is running on the same host as Kodi this is probably incorrect, and will result in errors.

The Stash host can be changed in the addon settings.

## Known Issues

- Galleries are listed when the addon is accessed via the _Video Addons_ section, but gallery images don't display.
  
  Likewise for Scenes under the _Picture Addons_ section.

- Some GraphQL queries could be better optimized.


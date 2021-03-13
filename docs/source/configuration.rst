Pipeline Configuration
===================

The only parts in **config.yml** that you need to touch are:

**bing_key:**
    Put your Bing API key here. You only need a Bing API key if you intend to run *registry_creator.py*. The API key is needed to translate the latitude and longitude values of detected PV systems into actual street addresses.

**county4analysis:**
    Specify the county in North Rhine-Westphalia for which you want to run the analysis by name, e.g. *Essen*.

**run_tile_creator:**
    Put 1 if you would like to execute this pipeline step and 0 if you would like to skip it.

**run_tile_downloader:**
    Put 1 if you would like to execute this pipeline step and 0 if you would like to skip it.

**run_tile_processor:**
    Put 1 if you would like to execute this pipeline step and 0 if you would like to skip it.

**run_tile_coords_updater:**
    Put 1 if you would like to execute this pipeline step and 0 if you would like to skip it.

**run_registry_creator:**
    Put 1 if you would like to execute this pipeline step and 0 if you would like to skip it.
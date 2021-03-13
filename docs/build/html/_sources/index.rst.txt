.. PV4GER documentation master file, created by
   sphinx-quickstart on Fri Mar 12 15:47:00 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PV4GER's documentation!
==================================

Introduction
===================

PV4GER aims at democratizing and accelerating the access to photovoltaic (PV) systems data in Germany and beyond. To do so, we have developed a computer vision-based pipeline which leverages 3D building data to automatically create address-level PV registries for all counties within Germany's most populous state North Rhine-Westphalia.

For a detailed description of the underlying pipeline and a case study for the city of Bottrop, please have a look at our spotlight talk *"An Enriched Automated PV Registry: Combining Image Recognition and 3D Building Data"* at NeurIPS 2020:

- `Paper <https://www.climatechange.ai/papers/neurips2020/46/paper.pdf>`_
- `Slides <https://www.climatechange.ai/papers/neurips2020/46/slides.pdf>`_
- `Recorded Talk <https://slideslive.com/38942134/an-enriched-automated-pv-registry-combining-image-recognition-and-3d-building-data>`_

Workflow
===================

To execute the pipeline for a given county, make sure that you have:

1. Downloaded the pre-trained model weights for PV classification and segmentation from our public S3 bucket.
2. Set up and activated your local virtual environment based on the provided *requirements.txt*.
3. Downloaded the .GeoJSON with all the rooftop information for your selected county from our public S3 bucket.
4. Set up the config.yml appropriately before executing *run_pipeline.py*

Contents
===================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   configuration
   tile_creator
   tile_downloader
   tile_processor
   tile_updater
   registry_creator
   supplementary_info


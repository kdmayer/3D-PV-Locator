# 3D-PV-Locator

![Pipeline Overview](https://github.com/kdmayer/3D-PV-Locator/blob/master/pipeline_visualization_new.png)

Repo with [documentation](docs/_build/rinoh/pv4ger.pdf) for "3D-PV-Locator: Large-scale detection of rooftop-mounted photovoltaic systems in 3D" published in [Applied Energy](https://www.sciencedirect.com/science/article/pii/S0306261921016937?via%3Dihub).

3D-PV-Locator is a joint research initiative between [Stanford University](http://web.stanford.edu/group/energyatlas/home.html), [University of Freiburg](https://www.is.uni-freiburg.de/research/smart-cities-industries-group/smart-cities-industries-sci-group), and [LMU Munich](https://www.en.compecon.econ.uni-muenchen.de/staff/postdocs/arlt1/index.html) that aims at democratizing and accelerating the access to photovoltaic (PV) systems data in Germany and beyond. 

To do so, we have developed a computer vision-based pipeline leveraging aerial imagery with a spatial resolution of
10 cm/pixel and 3D building data to automatically create address-level and rooftop-level PV registries for all counties
within Germany's most populous state North Rhine-Westphalia.

![Exemplary Pipeline Output](https://github.com/kdmayer/3D-PV-Locator/blob/master/exemplary_pipeline_output.png)

### Address-level registry

For every address equipped with a PV system in North Rhine-Westphalia, the automatically produced address-level
registry in GeoJSON-format specifies the respective PV system's: 

- geometry: Real-world coordinate-referenced polygon describing the shape of the rooftop-mounted PV system
- area_inter: The total area covered by the PV system in square meters
- area_tilted: The total area covered by the PV system in square meters, corrected by the respective rooftop tilt
- capacity_not_tilted_area: The total PV capacity in kWp of area_inter
- capacity_titled_area: The total PV capacity in kWp of area_tilted 
- location of street address in latitude and longitude 
- street address
- city and
- ZIP code

### Rooftop-level registry

For every rooftop equipped with a PV system in North Rhine-Westphalia, the automatically produced rooftop-level
registry in GeoJSON-format specifies the respective PV system's: 

- Azimuth: Orientation of the rooftop-mounted PV system, with 0° pointing to the North
- Tilt: Tilt of the rooftop-mounted PV system, with 0° being flat
- RoofTopID: Identifier of the respective rooftop
- geometry: Real-world coordinate-referenced polygon describing the shape of the rooftop-mounted PV system
- area_inter: The total area covered by the PV system in square meters
- area_tilted: The total area covered by the PV system in square meters, corrected by the respective rooftop tilt
- capacity_not_tilted_area: The total PV capacity in kWp of area_inter
- capacity_titled_area: The total PV capacity in kWp of area_tilted
- street address
- city and
- ZIP code 

For a detailed description of the underlying pipeline and a case study for the city of Bottrop, please have a look at our spotlight talk at NeurIPS 2020:

- [Paper](https://www.climatechange.ai/papers/neurips2020/46/paper.pdf)
- [Slides](https://www.climatechange.ai/papers/neurips2020/46/slides.pdf)
- [Recorded Talk](https://slideslive.com/38942134/an-enriched-automated-pv-registry-combining-image-recognition-and-3d-building-data)

You might also want to take a look at other projects within Stanford's EnergyAtlas initiative:

- [EnergyAtlas](http://web.stanford.edu/group/energyatlas/home.html)
- DeepSolar for Germany: [Publication](https://ieeexplore.ieee.org/document/9203258) and [Code](https://github.com/kdmayer/PV_Pipeline)

# Public S3 Bucket: PV4GER

Please note that apart from the pipeline code and documentation, we also provide you with

- A **pre-trained model checkpoint for PV classification** on aerial imagery with a spatial resolution of 10cm/pixel.
- A **pre-trained model checkpoint for PV segmentation** on aerial imagery with a spatial resolution of 10cm/pixel.
- A **100,000+ image dataset** for PV system classification.
- A **4,000+ image dataset** for PV system segmentation.
- **Pre-processed 3D building data** in .GeoJSON format for the entire state of North Rhine-Westphalia.

In case you use any of these, please cite our work as specified at the bottom of this page.

**NOTE**: All images and 3D building data is obtained from [openNRW](https://www.bezreg-koeln.nrw.de/brk_internet/geobasis/luftbildinformationen/aktuell/digitale_orthophotos/index.html). Labeling of the images for PV system classification and segmentation has been conducted by us.

## Usage Instructions:

    git clone https://github.com/kdmayer/3D-PV-Locator.git
    cd 3D-PV-Locator

Download pre-trained classification and segmentation models for PV systems from our public AWS S3 bucket. This bucket is in "requester pays" mode, which means that you need to configure your AWS CLI before being able to download the files. Instructions on how to do it can be found [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html).

Once you have configured your AWS CLI with 

    aws configure

you can list and browse our public bucket with

    aws s3 ls --request-payer requester s3://pv4ger/
    
Please download our pre-trained networks for PV system classification and segmentation by executing

    aws s3 cp --request-payer requester s3://pv4ger/NRW_models/inceptionv3_weights.tar models/classification/
    aws s3 cp --request-payer requester s3://pv4ger/NRW_models/deeplabv3_weights.tar models/segmentation/
    
Next, set up your conda environment with all required dependencies by executing

    conda env create --file environment.yml
    conda activate pv4ger
    
Lastly, to create PV registries for any county within North Rhine-Westphalia, you need to 

1. Download the 3D building data for your desired county from our S3 bucket by executing and replacing <YOUR_DESIRED_COUNTY.geojson> with a county name from the list below:

        aws s3 cp --request-payer requester s3://pv4ger/NRW_rooftop_data/<YOUR_DESIRED_COUNTY.geojson> data/nrw_rooftop_data/
        
    Example for the county of **Essen**:
    
        aws s3 cp --request-payer requester s3://pv4ger/NRW_rooftop_data/Essen.geojson data/nrw_rooftop_data/

2. Specify the name of your desired county for analysis in the config.yml next to the "county4analysis" element by
 choosing one of the counties from the list below:

    Example:
        
        county4analysis: Essen
        
3. **OPTIONAL STEP**: Obtain your Bing API key for geocoding from [here](https://docs.microsoft.com/en-us/bingmaps/getting-started/bing-maps-dev-center-help/getting-a-bing-maps-key) and paste it in the config.yml file next to the "bing_key" element

    Example:
    
        bing_key: <YOUR_BING_KEY>
    
    **NOTE**: If you leave <YOUR_BING_KEY> empty, geocoding will be done by the free OSM geocoding service.

4. Put a "1" next to all the pipeline steps that you would like to run

    Example:
    
        run_tile_creator: 1

        run_tile_downloader: 1

        run_tile_processor: 1

        run_tile_coords_updater: 0

        run_registry_creator: 1
        
   and execute run_pipeline.py in the root directory.
        
## List of available counties:
        
Please choose the county you would like to run the pipeline for from the following list:

- Düren
- Essen
- Unna
- Mönchengladbach
- Solingen
- Dortmund
- Gütersloh
- Olpe
- Steinfurt
- Bottrop
- Coesfeld
- Leverkusen
- Köln
- Soest
- Mülheim-a.d.-Ruhr
- Münster
- Heinsberg
- Oberhausen
- Euskirchen
- Krefeld
- Warendorf
- Recklinghausen
- Bochum
- Rhein-Kreis-Neuss
- Rheinisch-Bergischer-Kreis
- Herne
- Kleve
- Bonn
- Minden-Lübbecke
- Herford
- Rhein-Sieg-Kreis
- Düsseldorf
- Hagen
- Paderborn
- Wuppertal
- Oberbergischer-Kreis
- Viersen
- Rhein-Erft-Kreis
- Märkischer-Kreis
- Städteregion-Aachen
- Remscheid
- Mettmann
- Lippe
- Ennepe-Ruhr-Kreis
- Hochsauerlandkreis
- Gelsenkirchen
- Höxter
- Borken
- Hamm
- Bielefeld
- Duisburg
- Siegen-Wittgenstein
- Wesel 

## OpenNRW Platform:

For the German state of North Rhine-Westphalia (NRW), OpenNRW provides:

- Aerial imagery at a spatial resolution of 10cm/pixel
- Extensive 3D building data in CityGML format

## License:

[MIT](https://github.com/kdmayer/PV_Pipeline/blob/master/LICENSE)

## BibTex Citation:

Please cite our work as

    @article{Mayer2021,
      title={3D-PV-Locator: Large-scale detection of rooftop-mounted photovoltaic systems in 3D}, 
      author={Mayer, Kevin and Rausch, Benjamin and Arlt, Marie-Louise and Gust, Gunther and Wang, Zhecheng and Neumann, Dirk and Rajagopal, Ram},
      journal={Applied Energy},
      volume={310},
      year={2021},
      publisher={Elsevier}
    }




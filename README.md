# PV4GER

![Pipeline overview](https://github.com/kdmayer/PV4GER/blob/master/pipeline_visualization.png)

Repo with [documentation](docs/_build/rinoh/pv4ger.pdf) for "An Enriched Automated PV Registry: Combining Image Recognition and 3D Building Data"

PV4GER aims at democratizing and accelerating the access to photovoltaic (PV) systems data in Germany and beyond. To do so, we have developed a computer vision-based pipeline which leverages 3D building data to automatically create address-level PV registries for all counties within Germany's most populous state North Rhine-Westphalia.

For a detailed description of the underlying pipeline and a case study for the city of Bottrop, please have a look at our spotlight talk at NeurIPS 2020:

- [Paper](https://www.climatechange.ai/papers/neurips2020/46/paper.pdf)
- [Slides](https://www.climatechange.ai/papers/neurips2020/46/slides.pdf)
- [Recorded Talk](https://slideslive.com/38942134/an-enriched-automated-pv-registry-combining-image-recognition-and-3d-building-data)

You might also want to take a look at other projects within Stanford's EnergyAtlas initiative:

- [EnergyAtlas](http://web.stanford.edu/group/energyatlas/home.html)
- [DeepSolar for Germany](https://ieeexplore.ieee.org/document/9203258)

## Usage Instructions:

    git clone https://github.com/kdmayer/PV4GER.git
    cd PV4GER

Download pre-trained classification and segmentation models for PV systems from our public AWS S3 bucket. This bucket is in "requester pays" mode, which means that you need to configure your AWS CLI before being able to download the files. Instructions on how to do it can be found [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html).

Once you have configured your AWS CLI with 

    aws configure

you can list and browse our public bucket containing **pre-trained model checkpoints, classification and segmentation datasets, as well as extensive 3D building data in .GeoJSON format** with

    aws s3 ls --request-payer requester s3://pv4ger/
    
Please download our pre-trained networks for PV system classification and segmentation by executing

    aws s3 cp --request-payer requester s3://pv4ger/NRW_models/inceptionv3_weights.tar models/classification/
    aws s3 cp --request-payer requester s3://pv4ger/NRW_models/deeplabv3_weights.tar models/segmentation/
    
Next, set up your conda environment with all required dependencies by executing

    conda create --name PV4GER --file requirements.txt
    conda activate PV4GER
    
Lastly, to create PV registries for any county within North Rhine-Westphalia, you need to 

1. Download the 3D building data for your desired county from our S3 bucket by executing and replacing <YOUR_DESIRED_COUNTY.geojson> 

        aws s3 cp --request-payer requester s3://pv4ger/NRW_rooftop_data/<YOUR_DESIRED_COUNTY.geojson> data/nrw_rooftop_data/
        
    Example for the county of **Essen**:
    
        aws s3 cp --request-payer requester s3://pv4ger/NRW_rooftop_data/Essen.geojson data/nrw_rooftop_data/
     
2. Obtain your Bing API key for geocoding from [here](https://docs.microsoft.com/en-us/bingmaps/getting-started/bing-maps-dev-center-help/getting-a-bing-maps-key) and paste it in the config.yml file next to the "bing_key" element

    Example:
    
        bing_key: <YOUR_BING_KEY>

3. Specify the name of your desired county for analysis in the config.yml next to the "county4analysis" element 

    Example:
        
        county4analysis: Essen
    

## OpenNRW Platform:

For the German state of North Rhine-Westphalia (NRW), OpenNRW provides:

- Aerial imagery at a spatial resolution of 10cm/pixel
- Extensive 3D building data in CityGML format

## License:

[MIT](https://github.com/kdmayer/PV_Pipeline/blob/master/LICENSE)

## BibTex Citation:

Please cite our work as

    @misc{rausch2020enriched,
      title={An Enriched Automated PV Registry: Combining Image Recognition and 3D Building Data}, 
      author={Benjamin Rausch and Kevin Mayer and Marie-Louise Arlt and Gunther Gust and Philipp Staudt and Christof Weinhardt and Dirk Neumann and Ram Rajagopal},
      year={2020},
      eprint={2012.03690},
      archivePrefix={arXiv},
      primaryClass={cs.CV}
    }


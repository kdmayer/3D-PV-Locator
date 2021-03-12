import csv
import os
import pickle
import json
from itertools import chain
from shapely.geometry.polygon import Polygon
import threading
import shutil
import requests
from pathlib import Path

class TileDownloader(object):
    """
    Class to download tiles from the openNRW web server in a multi-threaded fashion.
    
    Attributes
    ----------
    tile_dir : str
        Path to directory where all the downloaded tiles are saved.
    downloaded_path : Path
        Specifies the path to the document which saves all the tiles by their minx, miny, maxx, maxy coordinates which were successfully downloaded.
    not_downloaded_path : Path
        Specifies the path to the document which saves all the tiles by their minx, miny, maxx, maxy coordinates which were **not** successfully downloaded.
    WMS_1 : str
        Initial URL stub for requests to the openNRW server.
    WMS_2 : str
        Final URL stub for requests to the openNRW server.
    NUM_THREADS : int
        Number of threads used to simultaneously download tiles from the openNRW server. 
    """

    def __init__(self, configuration, polygon, tile_coords):
        """
        Sets instance variables and starts donwloading process in a multi-threaded fashion
        
        Parameters
        ----------
        configuration : dict
            config.yml in dict format.
        polygon : shapely.geometry.polygon.Polygon
            Geo-referenced polygon geometry for the selected county within NRW.
        tile_coords : list
            List of tuples where each tuple specifies its respective tile by minx, miny, maxx, maxy.
        """

        self.polygon = polygon

        self.tile_coords = tile_coords

        self.tile_dir = configuration['tile_dir']

        self.downloaded_path = Path(f"logs/downloading/{configuration.get('county4analysis')}_downloadedTiles.csv")

        self.not_downloaded_path = Path(f"logs/downloading/{configuration.get('county4analysis')}_notDownloadedTiles.csv")

        # URL dummy for image request from open NRW server
        self.WMS_1 = 'https://www.wms.nrw.de/geobasis/wms_nw_dop?SERVICE=WMS&REQUEST=GetMap&Version=1.1.1&LAYERS=nw_dop_rgb&SRS=EPSG:4326&BBOX='

        self.WMS_2 = '&WIDTH=4800&HEIGHT=4800&FORMAT=image/png;%20mode=8bit'

        self.NUM_THREADS = 4

        download_threads = []

        for num in range(0, self.NUM_THREADS):
            # Download_threads is a list which contains thread objects that get passed their respective function to execute, here the download function, and the necessary arguments to execute that
            # function in form of a tuple
            download_threads.append(threading.Thread(target=self.download, args=(self.tile_coords, num,)))

        for num in range(0, self.NUM_THREADS):
            # Iterate over all thread objects and start them
            download_threads[num].start()

            print('Successfully started thread ' + str(num))

        for t in download_threads:
            # Iterate over all threads and execute them
            t.join()

    def download(self, Tile_coords, threadCounter):
        """
        Download tiles from openNRW's web servers.
        
        Parameters
        ----------
        Tile_coords : list
            List of tuples. Each tuple specifies its respective tile by minx, miny, maxx, maxy.
        threadCounter : int
            ID to distinguish between the different threads working in parallel.


        Returns
        -------

        """
        
        for index, tile in enumerate(Tile_coords):

            if index % self.NUM_THREADS == threadCounter:

                minx, miny, maxx, maxy = tile

                # cease when disk space not enough
                while 1:

                    st = os.statvfs(self.tile_dir)

                    # f_frsize − fundamental file system block size.
                    # f_bavail − free blocks available to non-super user.
                    # Storage capacity can be calculated by multiplying number of free blocks * block size
                    # Remember: 1 KB are 1024 Bytes. Hence, 1 MB are 1024*1024 Bytes
                    remain_capacity = st.f_bavail * st.f_frsize / 1024 / 1024

                    # if remain_capacity is larger than 1 GB, continue downloading tiles
                    if remain_capacity > 1024:

                        break

                    print(str(threadCounter), ": Disk space not enough!")

                try:

                    current_save_path = os.path.join(self.tile_dir, str(minx) + ',' + str(miny) + ',' + str(maxx) + ',' + str(maxy) +  '.png')

                    # Specify URL from which we download our tile
                    url = os.path.join(self.WMS_1 + str(minx) + ',' + str(miny) + ',' + str(maxx) + ',' + str(maxy) + self.WMS_2)

                    # Download tile imagery from URL
                    response = requests.get(url, stream=True)

                    # Save downloaded file under current_save_path
                    with open(current_save_path, 'wb') as out_file:

                        response.raw.decode_content = True

                        shutil.copyfileobj(response.raw, out_file)

                    del response

                    # This line will execute only after the whole tile has been downloaded
                    # Once the tile is completely downloaded, we add a 'COMPLETE' string at
                    # the end of its path to signal the Tile_Processing script which tiles
                    # are ready to be processed
                    os.rename(current_save_path, os.path.join(current_save_path[:-4] + ',COMPLETE.png'))

                    with open(Path(self.downloaded_path), "a") as csvFile:

                        writer = csv.writer(csvFile, lineterminator="\n")

                        writer.writerow([str(tile)])

                # Only tiles that weren't fully downloaded are saved subsequently
                except:

                    with open(Path(self.not_downloaded_path),"a") as csvFile:

                        writer = csv.writer(csvFile, lineterminator="\n")

                        writer.writerow([str(tile)])


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


# This script makes requests to the open NRW web server in order to download geospatial tile imagery.

class TileDownloader(object):

    def __init__(self, configuration, polygon, tile_coords):

        self.polygon = polygon

        self.tile_coords = tile_coords

        self.tile_dir = configuration['tile_dir']

        self.downloaded_path = configuration['downloaded_path']

        self.not_downloaded_path = configuration['not_downloaded_path']

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

        # Only tiles where at least one corner is within the NRW polygon
        # will be downloaded. In a second step, i.e. when splitting the tiles, only those images will be processed
        # where the centerpoint lies within the NRW polygon.

        # Tile_coords is a list of tuples. Each tuple specifies its respective tile by minx, miny, maxx, maxy
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


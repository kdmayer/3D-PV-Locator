# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 14:31:47 2019

@author: Kevin
"""
from __future__ import print_function
from __future__ import division

from src.utils.polygon_creator import PolygonCreator

from pathlib import Path
import torch
from torchvision import datasets, models, transforms, utils
from torchvision.models.segmentation.deeplabv3 import DeepLabHead
import csv
import os
import numpy as np
from itertools import compress
from shapely.geometry import Point, Polygon, MultiPolygon
from PIL import Image
from torch.nn import functional as F
from torchvision.models import Inception3
from torch.utils.data import Dataset, DataLoader
from src.dataset.dataset import NrwDataset
import sys

# Todo: Modularize __processTiles() by writing separate functions for classifying and segmenting a batch

class TileProcessor(object):

    def __init__(self, configuration, polygon):

        # Execute on gpu, if available
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        # ------ Load model configuration ------
        self.cls_threshold = configuration['cls_threshold']

        self.seg_threshold = configuration['seg_threshold']

        # Batch size should be as large as possible to speed up the classification process
        self.batch_size = configuration['batch_size']

        self.input_size = configuration['input_size']

        # ------ Specify required input directories ------
        self.cls_checkpoint_path = configuration['cls_checkpoint_path']

        self.seg_checkpoint_path = configuration['seg_checkpoint_path']

        self.tile_dir = configuration['tile_dir']

        # ------ Specify required output directories ------
        self.pv_db_path = configuration['pv_db_path']

        self.processed_path = configuration['processed_path']

        self.not_processed_path = configuration['not_processed_path']

        # ------ Load model and dataset ------
        self.cls_model = self.__loadClsModel()

        self.seg_model = self.__loadSegModel()

        self.dataset = NrwDataset(self.tile_dir)

        # ------ Set auxiliary instance variables ------
        self.polygon = polygon

        # Avg. earth radius in meters
        self.radius = 6371000

        # Square side length in meters
        self.side = 16

        # Number of image pixels along an axis
        self.size = 320

        # dlat spans a distance of 16 meters in north-south direction:
        self.dlat = (self.side * 360) / (2 * np.pi * self.radius)

        self.polygonCreator = PolygonCreator(self.size, self.side, self.radius, self.dlat)

    def __loadClsModel(self):

        # Specify model architecture
        cls_model = Inception3(num_classes=2, aux_logits=True, transform_input=False)
        cls_model = cls_model.to(self.device)

        # Load old parameters
        checkpoint = torch.load(self.cls_checkpoint_path, map_location=self.device)

        if self.cls_checkpoint_path[-4:] == '.tar':  # it is a checkpoint dictionary rather than just model parameters

            cls_model.load_state_dict(checkpoint['model_state_dict'])

        else:

            cls_model.load_state_dict(checkpoint)

        # Put model into inference mode
        cls_model.eval()

        return cls_model

    def __loadSegModel(self):

        seg_model = models.segmentation.deeplabv3_resnet101(pretrained=True, progress=True)

        seg_model.classifier = DeepLabHead(2048, 1)

        checkpoint = torch.load(self.seg_checkpoint_path, map_location=self.device)

        seg_model.load_state_dict(checkpoint['model_state_dict'])

        seg_model.eval()

        return seg_model

    def __splitTile(self, tile, minx, miny, maxx, maxy):

        minx = float(minx)
        miny = float(miny)
        maxx = float(maxx)
        maxy = float(maxy)

        # Takes a 4800x4800 image tile and returns a list of 320x320 pixel images, if they are within
        # the NRW polygon

        tile = np.array(tile)

        images = []
        coords = []

        N = 0
        S = 4800
        W = 0
        E = 4800

        # The first image is taken from the upper left corner, we then slide from left
        # to right and from top to bottom. Each image shall cover an area of 16x16m
        # and shall be identified by the coordinates of its upper left corner.
        y_coord = maxy

        while N < S:

            W = 0

            x_coord = minx

            while W < E:
                # The first image is taken from the upper left corner, we then slide from left
                # to right and from top to bottom

                images.append(tile[N:N + 320, W:W + 320])
                coords.append((x_coord, y_coord))

                x_coord += (((self.side * 360) / (2 * np.pi * self.radius * np.cos(np.deg2rad(y_coord)))))

                W = W + 320

            N = N + 320

            y_coord = y_coord - self.dlat

        # A boolean vector of length 225 indicating whether an image's upper left coordinate is within the NRW polygon
        coords_boolean = [self.polygon.intersects(Point(elem)) for elem in coords]

        # A list containing all images from the current tile that lie within NRW
        imagesInNRW = list(compress(images, coords_boolean))
        coordsInNRW = list(compress(coords, coords_boolean))

        return coordsInNRW, imagesInNRW

    def __processTiles(self, currentTile, trans_cls, trans_seg):

        # Load image tile
        tile = Image.open(Path(self.tile_dir + "/" + currentTile))

        if not tile.mode == 'RGB':
            tile = tile.convert('RGB')

        print("New tile with dimension:", tile.size)
        currentTile = currentTile[:-13]
        minx, miny, maxx, maxy = currentTile.split(',')
        coords, images = self.__splitTile(tile, minx, miny, maxx, maxy)
        length = len(images)
        if length == 0:
            pass
        else:
            k = int(length / self.batch_size)

            for i in range(k):

                print("batch:", i+1, "of:", k)

                img_batch = images[self.batch_size * i:self.batch_size * (i + 1)]
                coords4batch = coords[self.batch_size * i:self.batch_size * (i + 1)]

                # Image.fromarray() converts a numpy array into a PIL image
                # trans_cls() and trans_seg() apply image transformations such as resizing or normalization and convert a PIL image to a tensor
                # torch.unsqueeze(image tensor, 0) adds a new dimension at the specified position, e.g.
                # converting our image tensor from [3,299,299] to [1,3,299,299]
                batch4cls = [torch.unsqueeze(trans_cls(Image.fromarray(image)), 0) for image in img_batch]
                batch4seg = [torch.unsqueeze(trans_seg(Image.fromarray(image)), 0) for image in img_batch]

                # torch.cat(image tensor, dim=0) concatenates our image tensor along dimension 0, i.e. a list
                # of tensors of the form [1,3,299,299] is converted into a tensor of form [N,3,299,299]
                batch4cls = torch.cat(batch4cls, dim=0)
                batch4seg = torch.cat(batch4seg, dim=0)

                # Classify batch
                cls_outputs = self.cls_model(batch4cls)
                cls_prob = F.softmax(cls_outputs, dim=1)

                # detach() detaches the output from the computational graph.
                # So no gradient will be backproped along this variable.
                # For example if you’re computing some indices from the output of the
                # network and then want to use that to index a tensor. The indexing operation
                # is not differentiable wrt the indices. So you should detach() the indices
                # before providing them.
                cls_prob = cls_prob.cpu().detach().numpy()

                # PV_bool is a boolean array in which TRUE values correspond to images in our batch which depict PV systems
                PV_bool = cls_prob[:, 1] >= self.cls_threshold

                # If our batch contains positively classified images, we pass them to the segmentation model
                if PV_bool.sum() > 0:

                    # Select all images which depict PV systems and their respective coordinates (upper left image corner)
                    batch4seg = batch4seg[PV_bool]
                    coords4seg = list(compress(coords4batch, PV_bool))
                    # self.seg_model.cuda()
                    seg_outputs = self.seg_model(batch4seg)
                    seg_outputs = seg_outputs['out'].squeeze(1)
                    seg_outputs = seg_outputs.detach().cpu().numpy()
                    # min-max scaling
                    seg_outputs = (seg_outputs - np.min(seg_outputs)) / (
                                np.max(seg_outputs) - np.min(seg_outputs) + 0.000000001)
                    # setting a threshold to turn CAMs into binary segmentation masks
                    seg_outputs = seg_outputs >= self.seg_threshold
                    # Turn class activation maps (CAMs) into binary segmentation masks
                    seg_masks = [CAM.astype(np.int32) for CAM in seg_outputs]
                    # Only consider binary segmentation masks with at least one positive pixel
                    # I.e. ignore instances where an image is positively classified, but the segmentation model does not activate any pixels
                    PV_bool_seg = [True if seg_mask.sum() >= 1 else False for seg_mask in seg_masks]
                    PV_masks = list(compress(seg_masks, PV_bool_seg))
                    PV_image_coords = list(compress(coords4seg, PV_bool_seg))

                    # Iterate over all PV masks and store the polygon for each detected PV system in a .csv file
                    for idx, mask in enumerate(PV_masks):

                        polygon_gdf = self.polygonCreator.mask2polygon(PV_image_coords[idx], mask)

                        with open(Path(self.pv_db_path), "a") as csvFile:

                            fieldnames = ['Current_Tile_240', 'UL_Image_16', 'PV_polygon']
                            writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=';')

                            for index, row in polygon_gdf.iterrows():

                                if row['class'] == 1:

                                    writer.writerow({'Current_Tile_240': currentTile,
                                                     'UL_Image_16': Point(PV_image_coords[idx]),
                                                     'PV_polygon': row['geometry']})

            # Repeat process for last batch
            img_batch = images[self.batch_size * i:self.batch_size * (i + 1)]
            coords4batch = coords[self.batch_size * i:self.batch_size * (i + 1)]

            batch4cls = [torch.unsqueeze(trans_cls(Image.fromarray(image)), 0) for image in img_batch]
            batch4seg = [torch.unsqueeze(trans_seg(Image.fromarray(image)), 0) for image in img_batch]

            batch4cls = torch.cat(batch4cls, dim=0)
            batch4seg = torch.cat(batch4seg, dim=0)

            # Classify batch
            cls_outputs = self.cls_model(batch4cls)

            cls_prob = F.softmax(cls_outputs, dim=1)
            cls_prob = cls_prob.cpu().detach().numpy()

            # PV_bool is a boolean array in which TRUE values correspond to images in our batch which depict PV systems
            PV_bool = cls_prob[:, 1] >= self.cls_threshold

            # If our batch contains positively classified images, we pass them to the segmentation model
            if PV_bool.sum() > 0:

                # Select all images which depict PV systems and their respective coordinates (upper left image corner)
                batch4seg = batch4seg[PV_bool]
                coords4seg = list(compress(coords4batch, PV_bool))
                # self.seg_model.cuda()
                seg_outputs = self.seg_model(batch4seg)
                seg_outputs = seg_outputs['out'].squeeze(1)
                seg_outputs = seg_outputs.detach().cpu().numpy()
                # min-max scaling
                seg_outputs = (seg_outputs - np.min(seg_outputs)) / (
                            np.max(seg_outputs) - np.min(seg_outputs) + 0.000000001)
                # setting a threshold to turn CAMs into binary segmentation masks
                seg_outputs = seg_outputs >= self.seg_threshold
                # Turn class activation maps (CAMs) into binary segmentation masks
                seg_masks = [CAM.astype(np.int32) for CAM in seg_outputs]
                # Only consider binary segmentation masks with at least one positive pixel
                # I.e. ignore instances where an image is positively classified, but the segmentation model does not activate any pixels
                PV_bool_seg = [True if seg_mask.sum() >= 1 else False for seg_mask in seg_masks]
                PV_masks = list(compress(seg_masks, PV_bool_seg))
                PV_image_coords = list(compress(coords4seg, PV_bool_seg))

                # Iterate over all PV masks and store the polygon for each detected PV system in a .csv file
                for idx, mask in enumerate(PV_masks):

                    polygon_gdf = self.polygonCreator.mask2polygon(PV_image_coords[idx], mask)

                    with open(Path(self.pv_db_path), "a") as csvFile:

                        fieldnames = ['Current_Tile_240', 'UL_Image_16', 'PV_polygon']
                        writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=';')

                        for index, row in polygon_gdf.iterrows():

                            if row['class'] == 1:
                                writer.writerow({'Current_Tile_240': currentTile,
                                                 'UL_Image_16': Point(PV_image_coords[idx]),
                                                 'PV_polygon': row['geometry']})

    def run(self):

        print('Dataset Size:', len(self.dataset))

        dataloader = DataLoader(self.dataset, batch_size=1, num_workers=0)

        trans_cls = transforms.Compose([
            transforms.Resize(self.input_size),
            transforms.ToTensor(),
            transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
        ])

        trans_seg = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
        ])

        for i, batch in enumerate(dataloader):

            currentTile = batch[0]

            # Try to process and record it
            # try:

            self.__processTiles(currentTile, trans_cls, trans_seg)

            with open(Path(self.processed_path), "a") as csvFile:

                writer = csv.writer(csvFile, lineterminator="\n")

                writer.writerow([currentTile])

            # Only tiles that weren't fully processed are saved subsequently
            # ToDo: Catch the exception and write it in a second column in the .csv
            '''
            except:

                e = sys.exc_info()[0]

                # Save the tile which could not be processed and continue
                with open(Path(self.not_processed_path), "a") as csvFile:

                    writer = csv.writer(csvFile, lineterminator="\n")

                    writer.writerow([currentTile, e])
            '''
            # Delete iterated tile
            os.remove(Path(self.tile_dir + "/" + str(currentTile)))


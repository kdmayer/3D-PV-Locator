from __future__ import print_function
from __future__ import division
import os
from torch.utils.data import Dataset, DataLoader

'''
Customized Dataset for openNRW tiles
'''

class NrwDataset(Dataset):

    def __init__(self, data_root):

        self.samples = []

        for elem in os.listdir(data_root):

            if elem[-12:] == 'COMPLETE.png':

                self.samples.append((elem))

            else:

                continue

    def __len__(self):

        return len(self.samples)

    def __getitem__(self, idx):

        return self.samples[idx]
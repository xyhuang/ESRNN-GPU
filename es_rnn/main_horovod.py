import pandas as pd
import torch
from torch.utils.data import DataLoader
from es_rnn.data_loading import create_datasets, SeriesDataset
from es_rnn.config import get_config
from es_rnn.trainer_horovod import ESRNNTrainer
from es_rnn.model import ESRNN
import time

import horovod.torch as hvd

hvd.init()
torch.cuda.set_device(hvd.local_rank())

print('loading config')
config = get_config('Monthly')

print('loading data')
info = pd.read_csv('./data/info.csv')

train_path = './data/Train/%s-train.csv' % (config['variable'])
test_path = './data/Test/%s-test.csv' % (config['variable'])

train, val, test = create_datasets(train_path, test_path, config['output_size'])

dataset = SeriesDataset(train, val, test, info, config['variable'], config['chop_val'], config['device'])
train_sampler = torch.utils.data.distributed.DistributedSampler(
    dataset, num_replicas = hvd.size(), rank=hvd.rank())
dataloader = DataLoader(dataset, batch_size=config['batch_size'], sampler=train_sampler)

run_id = str(int(time.time()))
model = ESRNN(num_series=len(dataset), config=config)
tr = ESRNNTrainer(model, dataloader, run_id, config, ohe_headers=dataset.dataInfoCatHeaders)
tr.train_epochs()

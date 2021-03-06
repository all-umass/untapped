import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from collections import OrderedDict

import numpy as np
import lasagne
from untapped.parmesan.layers import SampleLayer
from untapped.parmesan.layers import NormalizingSimplexFlowLayer, LogisticFlowLayer

from untapped.M12 import L2, KL
from untapped.S2S_DGM import SSDGM
from untapped.utilities import timeStamp

from datasets.load_crism import load_process_data, get_endmembers
from plotting.plotting_crism import make_plots

#####################################################################
# REQUIRES optimizer='fast_compile' in .theanorc file under [global]
#####################################################################

# load data
remove_mean = True
xy, ux, waves, names, colors = load_process_data(remove_mean=remove_mean)
sup_train_x, sup_train_y, sup_valid_x, sup_valid_y, train_x, train_y = [xyi.astype('float32') for xyi in xy]

# define variable sizes
num_features = sup_train_x.shape[1]
num_output = sup_train_y.shape[1]
num_latent_z2 = 1

# construct data dictionary
data = {'X':sup_train_x,'y':sup_train_y,
        'X_':train_x,
        'X_valid':sup_valid_x,'y_valid':sup_valid_y,
        'X__valid':train_x}

# include "untapped" label source
data['_y'] = train_y
data['_y_valid'] = train_y
data['z2'] = np.random.uniform(low=-1.5, high=1.5, size=(train_y.shape[0], num_latent_z2)).astype('float32')
data['z2_valid'] = np.random.uniform(low=-1.5, high=1.5, size=(train_y.shape[0], num_latent_z2)).astype('float32')

# define priors
prior_x = None  # uniform distribution over positive intensities
prior_y = None  # uniform distribution over simplex
prior_z2 = None  # uniform distribution over interval

# define the model architecture (x=z1)
model_dict = OrderedDict()

arch = OrderedDict()
arch['hidden'] = [5]
arch['gain'] = np.sqrt(2)
arch['nonlin'] = lasagne.nonlinearities.tanh
arch['num_output'] = num_output
arch['sample_layer'] = SampleLayer
arch['flows'] = [NormalizingSimplexFlowLayer]
arch['batch_norm'] = False
model_dict['z1->y'] = OrderedDict([('arch',arch)])

arch = OrderedDict()
arch['hidden'] = [5]
arch['gain'] = np.sqrt(2)
arch['nonlin'] = lasagne.nonlinearities.tanh
arch['num_output'] = num_latent_z2
arch['sample_layer'] = SampleLayer
arch['flows'] = [LogisticFlowLayer]
arch['batch_norm'] = False
model_dict['z1y->z2'] = OrderedDict([('arch',arch)])

arch = OrderedDict()
arch['hidden'] = [20]
arch['gain'] = np.sqrt(2)
arch['nonlin'] = lasagne.nonlinearities.tanh
arch['num_output'] = num_features
arch['sample_layer'] = SampleLayer
arch['flows'] = []
arch['batch_norm'] = False
model_dict['yz2->_z1'] = OrderedDict([('arch',arch)])

# set result directory path
res_out='examples/results/crism/'+timeStamp().format("")

# construct the semi^2-supervised deep generative model
m = SSDGM(num_features,num_output,variational=True,model_dict=model_dict,
          prior_x=prior_x,prior_y=prior_y,prior_z2=prior_z2,loss_x=L2,loss_y=KL,
          coeff_x=1,coeff_y=1e-2,coeff_x_dis=1,coeff_y_dis=1,coeff_x_prob=1,coeff_y_prob=1e-2,
          num_epochs=5000,eval_freq=500,lr=3e-3,eq_samples=1,iw_samples=1,
          res_out=res_out)

# fit the model
m.fit(verbose=True,debug=False,**data)

# auto-set title and plot results (saved to res_out)
title = 'M2'
if m.coeff_y_dis > 0:
    if m.coeff_y > 0:
        title = 'Labels Untapped'
    else:
        title = r'Supervised ($\mathbf{y} \rightarrow \mathbf{x}$) M2'

make_plots(m,data,colors,names,groundtruth=get_endmembers()[:,1:][:,::-1].T,
           sample_size=10,ux=ux,remove_mean=remove_mean,res_out=res_out,title=title)

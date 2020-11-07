
import os
import ast 
import sys
import numpy as np
import yaml
import pkg_resources

def parse_version(version_string):
  '''
  Parses version string, discards last identifier (NR/alpha/beta) and returns an integer for comparison
  '''
  version_string_split = version_string.split('.')
  if len(version_string_split) > 3:
    del version_string_split[-1]
  return int(''.join(version_string_split))

def parseConfig(config_file_path):
  '''
  This function parses the configuration file and returns a dictionary of parameters
  '''
  with open(config_file_path) as f:
    params = yaml.load(f, Loader=yaml.FullLoader)
  
  if not('version' in params):
    sys.exit('The \'version\' key needs to be defined in config with \'minimum\' and \'maximum\' fields to determine the compatibility of configuration with code base')
  else:
    gandlf_version = pkg_resources.require('GANDLF')[0].version
    gandlf_version_int = parse_version(gandlf_version)
    min = parse_version(params['version']['minimum'])
    max = parse_version(params['version']['maximum'])
    if (min > gandlf_version_int) or (max < gandlf_version_int):
      sys.exit('Incompatible version of GANDLF detected (' + gandlf_version + ')')
      
  # require parameters - this should error out if not present
  if not('class_list' in params):
    sys.exit('The \'class_list\' parameter needs to be present in the configuration file')

  if not params['dimension']:
    sys.exit('The \'dimension\' parameter to be defined, which should be 2 or 3')

  if 'patch_size' in params:
    params['psize'] = params['patch_size'] 
  else:
    sys.exit('The \'patch_size\' parameter needs to be present in the configuration file')
  
  if 'resize' in params:
    if not np.greater_equal(params['resize'], params['psize']).all():
      sys.exit('The \'resize\' parameter needs to be greater than or equal to \'patch_size\'')
  else:
    params['resize'] = None

  # Extrating the training parameters from the dictionary
  if 'num_epochs' in params:
    num_epochs = int(params['num_epochs'])
  else:
    num_epochs = 100
    print('Using default num_epochs: ', num_epochs)
  params['num_epochs'] = num_epochs
  
  if 'patience' in params:
    patience = int(params['patience'])
  else:
    print("Patience not given, train for full number of epochs")
    patience = num_epochs
  params['patience'] = patience

  if 'batch_size' in params:
    batch_size = int(params['batch_size'])
  else:
    batch_size = 1
    print('Using default batch_size: ', batch_size)
  params['batch_size'] = batch_size
  
  if 'amp' in params:
    amp = bool(params['amp'])
  else:
    amp = False
    print("NOT using Mixed Precision Training")
  params['amp'] = amp

  if 'learning_rate' in params:
    learning_rate = float(params['learning_rate'])
  else:
    learning_rate = 0.001
    print('Using default learning_rate: ', learning_rate)
  params['learning_rate'] = learning_rate

  if 'loss_function' in params:
    defineDefaultLoss = False
    # check if user has passed a dict 
    if isinstance(params['loss_function'], dict): # if this is a dict
      if len(params['loss_function']) > 0: # only proceed if something is defined
        for key in params['loss_function']: # iterate through all keys
          if key == 'mse':
            if (params['loss_function'][key] == None) or not('reduction' in params['loss_function'][key]):
              params['loss_function'][key] = {}
              params['loss_function'][key]['reduction'] = 'mean'
          else:
            params['loss_function'] = key # use simple string for other functions - can be extended with parameters, if needed
      else:
        defineDefaultLoss = True
    else:      
      # check if user has passed a single string
      if params['loss_function'] == 'mse':
        params['loss_function'] = {}
        params['loss_function']['mse'] = {}
        params['loss_function']['mse']['reduction'] = 'mean'
  else:
    defineDefaultLoss = True
  if defineDefaultLoss == True:
    loss_function = 'dc'
    print('Using default loss_function: ', loss_function)
  else:
    loss_function = params['loss_function']
  params['loss_function'] = loss_function

  if 'opt' in params:
    opt = str(params['opt'])
  else:
    opt = 'adam'
    print('Using default opt: ', opt)
  params['opt'] = opt
  
  # this is NOT a required parameter - a user should be able to train with NO augmentations
  if len(params['data_augmentation']) > 0: # only when augmentations are defined
      keysToSkip = ['normalize', 'resample', 'threshold', 'clip']
      if not(key in keysToSkip): # no need to check probabilities for these: they should ALWAYS be added
        if (params['data_augmentation'][key] == None) or not('probability' in params['data_augmentation'][key]): # when probability is not present for an augmentation, default to '1'
            params['data_augmentation'][key] = {}
            params['data_augmentation'][key]['probability'] = 1
      else:
        print('WARNING: \'' + key + '\' should be defined under \'data_processing\' and not under \'data_augmentation\', this will be skipped', file = sys.stderr)

  # this is NOT a required parameter - a user should be able to train with NO built-in pre-processing 
  if len(params['data_preprocessing']) < 0: # perform this only when pre-processing is defined
    thresholdOrClip = False
    thresholdOrClipDict = ['threshold', 'clip'] # this can be extended, as required
    for key in params['data_preprocessing']: # iterate through all keys
      # for threshold or clip, ensure min and max are defined
      if not thresholdOrClip:
        if (key in thresholdOrClipDict):
          thresholdOrClip = True # we only allow one of threshold or clip to occur and not both
          if not(isinstance(params['data_preprocessing'][key], dict)):
            params['data_preprocessing'][key] = {}
          
          if not 'min' in params['data_preprocessing'][key]: 
            params['data_preprocessing'][key]['min'] = sys.float_info.min
          if not 'max' in params['data_preprocessing'][key]:
            params['data_preprocessing'][key]['max'] = sys.float_info.max
      else:
        sys.exit('Use only \'threshold\' or \'clip\', not both')

  # Extracting the model parameters from the dictionary
  if 'base_filters' in params:
    base_filters = int(params['base_filters'])
  else:
    base_filters = 30
    print('Using default base_filters: ', base_filters)
  params['base_filters'] = base_filters

  if 'modelName' in params:
    defineDefaultModel = False
    print('This option has been superceded by \'model\'', file=sys.stderr)
    which_model = str(params['modelName'])
  elif 'which_model' in params:
    defineDefaultModel = False
    print('This option has been superceded by \'model\'', file=sys.stderr)
    which_model = str(params['which_model'])
  else: # default case
    defineDefaultModel = True
  if defineDefaultModel == True:
    which_model = 'resunet'
    # print('Using default model: ', which_model)
  params['which_model'] = which_model

  if 'model' in params:

    if not(isinstance(params['model'], dict)):
      sys.exit('The \'model\' parameter needs to be populated as a dictionary')
    elif len(params['model']) == 0: # only proceed if something is defined
      sys.exit('The \'model\' parameter needs to be populated as a dictionary and should have all properties present')

    if not params['model']['architecture']:
      sys.exit('The \'model\' parameter needs \'architecture\' key to be defined')
    if not params['model']['final_layer']:
      sys.exit('The \'model\' parameter needs \'final_layer\' key to be defined')

  else:
    sys.exit('The \'model\' parameter needs to be populated as a dictionary')

  if 'kcross_validation' in params:
    sys.exit('\'kcross_validation\' is no longer used, please use \'nested_training\' instead')

  if not params['nested_training']:
    sys.exit('The parameter \'nested_training\' needs to be defined')
  if not params['nested_training']['holdout']:
    kfolds = -10
    print('Using default folds for holdout split: ', kfolds)
    params['nested_training']['holdout']
  if not params['nested_training']['validation']:
    kfolds = -10
    print('Using default folds for validation split: ', kfolds)
    params['nested_training']['validation']

  # Setting default values to the params
  if 'scheduler' in params:
      scheduler = str(params['scheduler'])
  else:
      scheduler = 'triangle'
  params['scheduler'] = scheduler

  if 'q_max_length' in params:
      q_max_length = int(params['q_max_length'])
  else:
      q_max_length = 100
  params['q_max_length'] = q_max_length

  if 'q_samples_per_volume' in params:
      q_samples_per_volume = int(params['q_samples_per_volume'])
  else:
      q_samples_per_volume = 10
  params['q_samples_per_volume'] = q_samples_per_volume

  if 'q_num_workers' in params:
      q_num_workers = int(params['q_num_workers'])
  else:
      q_num_workers = 4
  params['q_num_workers'] = q_num_workers

  q_verbose = False
  if 'q_verbose' in params:
      if params['q_verbose'] == 'True':
          q_verbose = True  
  params['q_verbose'] = q_verbose

  parallel_compute_command = ''
  if 'parallel_compute_command' in params:
      parallel_compute_command = params['parallel_compute_command']
      parallel_compute_command = parallel_compute_command.replace('\'', '')
      parallel_compute_command = parallel_compute_command.replace('\"', '')
  params['parallel_compute_command'] = parallel_compute_command

  return params

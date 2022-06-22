import yaml
import os
from copy import deepcopy

'''
proj_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
yaml_file = os.path.join(proj_dir, 'tpx3' + os.sep + 'dacs.yml')

chip_ID_int     = [3184, 4172, 8536, 9517]
chip_ID_decoded = ['W18-C7', 'W14-D6', 'W15-H3', 'W16-D4']

with open(yaml_file) as file:
    yaml_data = yaml.load(file, Loader=yaml.FullLoader)

#print(yaml_data)
#for chunk in yaml_data['registers']:
#data_chunk = yaml_data['registers'][:]['address']
    #print(chunk['address'], chunk['description'])

# Now build a DAC yaml specifically for each chip

dac_yaml = os.path.join(proj_dir, 'tpx3' + os.sep + 'chip_dacs.yml')

with open(dac_yaml, 'w') as file:
    
    full_chip_dict = []

    for chip in range(len(chip_ID_int)):
        
        chip_dict = {'chip_number': chip, 'chip_ID_int': chip_ID_int[chip], 'chip_ID_decoded': chip_ID_decoded[chip], 'registers': deepcopy(yaml_data['registers'])}
        full_chip_dict.append(chip_dict)
    
    yaml.dump({'chips': full_chip_dict}, file)

# just dump a couple of registers
with open(dac_yaml, 'r') as config:

    yaml_dacs = yaml.load(config, Loader= yaml.FullLoader)
    #chip_dicts = yaml_dacs['chips'][1]
    for chip_dicts in yaml_dacs['chips']:
        print(chip_dicts)
        #for indx, (number, chip_config) in enumerate(chip_dicts.items()):
        #    print(indx, number, chip_config)
        #print(chip_dicts[0]['chip_ID_decoded'])
'''

num = 'dec'

my_dict = { 'zero': 0, 'one': 1, 'two': (10 if num == 'bin' else 2)}

print(my_dict)
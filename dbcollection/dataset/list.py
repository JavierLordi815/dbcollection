"""
Datasets list.

All available datasets must be added in here.
"""


from . import image_processing


#---------------------------------------------------------
# Category lists
#---------------------------------------------------------

image_processing_list = {
    "cifar10": image_processing.cifar.cifar10.Cifar10,
    #"cifar100": image_processing.cifar.cifar100.Cifar100,
}


#---------------------------------------------------------
# MAIN list
#---------------------------------------------------------

dataset_list = {
    "image_processing": image_processing_list,
}
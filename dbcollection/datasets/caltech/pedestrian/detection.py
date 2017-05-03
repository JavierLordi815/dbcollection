"""
Caltech Pedestrian detection process functions.
"""


from __future__ import print_function, division
import os
import numpy as np
import h5py
import progressbar

from dbcollection.utils.file_load import load_json
from dbcollection.utils.string_ascii import convert_str_to_ascii as str2ascii
from dbcollection.utils.pad import pad_list
from dbcollection.utils.caltech_pedestrian_extractor.converter import extract_data


class Detection:
    """ Caltech Pedestrian detection preprocessing functions """

    # metadata filename
    filename_h5 = 'detection'

    skip_step = 30

    def __init__(self, data_path, cache_path, verbose=True):
        """
        Initialize class.
        """
        self.cache_path = cache_path
        self.data_path = data_path
        self.verbose = verbose
        self.extracted_data_path = os.path.join(data_path, 'extracted_data')


    def convert_extract_data(self):
        """
        Extract + convert .jpg + .json files from the .seq and .vbb files.
        """
        if not os.path.exists(self.extracted_data_path):
            extract_data(self.data_path, self.extracted_data_path)


    def load_data(self):
        """
        Load the data from the dataset's files.
        """
        # extract data
        self.convert_extract_data()

        self.classes = ['person', 'person-fa', 'people', 'person?']

        sets = {
            "train" : ['set00', 'set01', 'set02', 'set03', 'set04', 'set05'],
            "test" : ['set06', 'set07', 'set08', 'set09', 'set10']
        }

        for set_name in sets:
            data = {set_name : {}}

            if self.verbose:
                print('\n> Loading data files for the set: {}'.format(set_name))

            # progressbar
            if self.verbose:
                prgbar = progressbar.ProgressBar(max_value=len(sets[set_name]))


            for i, set_data in enumerate(sets[set_name]):
                data[set_name][set_data] = {}

                extracted_data_dir = os.path.join(self.extracted_data_path, set_data)

                # list all folders
                folders = os.listdir(extracted_data_dir)
                folders.sort()

                for video in folders:
                    # fetch all images filenames
                    img_fnames = os.listdir(os.path.join(extracted_data_dir, video, 'images'))
                    img_fnames = [os.path.join('extracted_data', set_data, video, 'images', fname) for fname in img_fnames]
                    img_fnames.sort()
                    img_fnames_list = [img_fnames[i] for i in range(self.skip_step-1, len(img_fnames), self.skip_step)]

                    # fetch all annotations filenames
                    annotation_fnames = os.listdir(os.path.join(extracted_data_dir, video, 'annotations'))
                    annotation_fnames = [os.path.join('extracted_data', set_data, video, 'annotations', fname) for fname in annotation_fnames]
                    annotation_fnames.sort()
                    annotation_fnames_list = [annotation_fnames[i] for i in range(self.skip_step-1, len(annotation_fnames), self.skip_step)]

                    data[set_name][set_data][video] = {
                        "images" : img_fnames_list,
                        "annotations" : annotation_fnames_list
                    }

                # update progressbar
                if self.verbose:
                    prgbar.update(i)

            # reset progressbar
            if self.verbose:
                prgbar.finish()

            yield data


    def store_data_source(self, handler, data, set_name):
        """
        Add data of a set to the source group.

        TODO: refactor to use groups by set, video and file+annot
        """
        if self.verbose:
            print('> Adding data to the source group')
            prgbar = progressbar.ProgressBar(max_value=len(data))

        # create set group
        set_name_grp = handler.create_group('source/' + set_name)

        for i, set_data in enumerate(sorted(data)):
            set_grp = set_name_grp.create_group(set_data)
            for video in sorted(data[set_data]):
                video_grp = set_grp.create_group(video)
                for j in range(len(data[set_data][video]['images'])):
                    file_grp = video_grp.create_group(str(j))
                    file_grp['image_filenames'] = str2ascii(data[set_data][video]['images'][j])
                    file_grp['annotation_filenames'] = str2ascii(data[set_data][video]['annotations'][j])

            # update progressbar
            if self.verbose:
                prgbar.update(i)

        # update progressbar
        if self.verbose:
            prgbar.finish()


    def store_data_default(self, handler, data, set_name):
        """
        Add data of a set to the default file.
        """
        object_fields = ['image_filenames', 'classes', 'boxes', 'boxesv', 'id', 'occlusion']
        image_filenames = []
        bbox = []
        bboxv = []
        lbl_id = []
        occlusion = []
        object_id = []

        list_image_filenames_per_class = []
        list_boxes_per_image = []
        list_boxesv_per_image = []
        list_object_ids_per_image = []
        list_objects_ids_per_class = []
        #list_objects_ids_per_id = []
        #list_objects_ids_per_occlusion= []

        if self.verbose:
            print('> Adding data to default file...')
            prgbar = progressbar.ProgressBar(max_value=len(data))

        img_counter = 0
        obj_counter = 0
        for i, set_data in enumerate(sorted(data)):
            for video in sorted(data[set_data]):
                img_fnames = data[set_data][video]["images"]
                annot_fnames = data[set_data][video]["annotations"]

                # cycle all images + annotations
                for j in range(0, len(img_fnames)):
                    # add image filename
                    image_filenames.append(img_fnames[j])

                    # load annotation file
                    annotation = load_json(os.path.join(self.data_path, annot_fnames[j]))

                    obj_per_img = []
                    if any(annotation):
                        for obj in annotation:
                            # convert [x,y,w,h] to [xmin,ymin,xmax,ymax]
                            if obj['pos'][2] >= 5 and obj['pos'][3] >= 5: # discard any bbox smaller than 5px wide/high
                                bb_correct_format = [obj['pos'][0],
                                                     obj['pos'][1],
                                                     obj['pos'][0] + obj['pos'][2]-1,
                                                     obj['pos'][1] + obj['pos'][3]-1]
                                bbox.append(bb_correct_format)
                                if isinstance(obj['posv'], list):
                                    # convert [x,y,w,h] to [xmin,ymin,xmax,ymax]
                                    bbv_correct_format = [obj['posv'][0],
                                                          obj['posv'][1],
                                                          obj['posv'][0] + obj['posv'][2]-1,
                                                          obj['posv'][1] + obj['posv'][3]-1]
                                    bboxv.append(bbv_correct_format)
                                else:
                                    bboxv.append([0, 0, 0, 0])
                                if isinstance(obj['id'], int):
                                    lbl_id.append(obj['id'])
                                else:
                                    lbl_id.append(0)
                                occlusion.append(obj['occl'])
                                class_lbl = self.classes.index(obj['lbl'])

                                # img, class, bbox, bboxv, id, occlusion
                                object_id.append([img_counter, class_lbl, obj_counter,
                                                  obj_counter, obj_counter, obj_counter])

                                obj_per_img.append(obj_counter)

                                # increment counter
                                obj_counter += 1

                    # add to lists
                    list_boxes_per_image.append(obj_per_img)
                    list_boxesv_per_image.append(obj_per_img)
                    list_object_ids_per_image.append(obj_per_img)

                    # increment counter
                    img_counter += 1

            # update progressbar
            if self.verbose:
                prgbar.update(i)

        # update progressbar
        if self.verbose:
            prgbar.finish()

        if self.verbose:
            print('> Processing lists...')

        # Process lists
        for i in range(len(self.classes)):
            imgs_per_class = [val[0] for j, val in enumerate(object_id) if val[1] == i]
            imgs_per_class = list(set(imgs_per_class)) # get unique values
            imgs_per_class.sort()
            list_image_filenames_per_class.append(imgs_per_class)

        for i in range(len(self.classes)):
            objs_per_class = [j for j, val in enumerate(object_id) if val[1] == i]
            objs_per_class = list(set(objs_per_class)) # get unique values
            objs_per_class.sort()
            list_objects_ids_per_class.append(objs_per_class)

        # add data to hdf5 file
        set_grp = handler.create_group('default/' + set_name)

        set_grp['image_filenames'] = str2ascii(image_filenames)
        set_grp['classes'] = str2ascii(self.classes)
        set_grp['boxes'] = np.array(bbox, dtype=np.float)
        set_grp['boxesv'] = np.array(bboxv, dtype=np.float)
        set_grp['id'] = np.array(lbl_id, dtype=np.int32)
        set_grp['occlusion'] = np.array(occlusion, dtype=np.float)
        set_grp['object_ids'] = np.array(object_id, dtype=np.int32)
        set_grp['object_fields'] = str2ascii(object_fields)

        set_grp['list_image_filenames_per_class'] = np.array(pad_list(list_image_filenames_per_class, -1), dtype=np.int32)
        set_grp['list_boxes_per_image'] = np.array(pad_list(list_boxes_per_image, -1), dtype=np.int32)
        set_grp['list_boxesv_per_image'] = np.array(pad_list(list_boxesv_per_image, -1), dtype=np.int32)
        set_grp['list_object_ids_per_image'] = np.array(pad_list(list_object_ids_per_image, -1), dtype=np.int32)
        set_grp['list_objects_ids_per_class'] = np.array(pad_list(list_objects_ids_per_class, -1), dtype=np.int32)

        if self.verbose:
            print('> Done.')


    def process_metadata(self):
        """
        Process metadata and store it in a hdf5 file.
        """
        # create/open hdf5 files with subgroups for train/val/test/etc
        file_name = os.path.join(self.cache_path, self.filename_h5 + '.h5')
        fileh5 = h5py.File(file_name, 'w', version='latest')

        if self.verbose:
            print('\n==> Storing metadata to file: {}'.format(file_name))

        # setup data generator
        data_gen = self.load_data()

        for data in data_gen:
            for set_name in data:

                if self.verbose:
                    print('Saving set metadata: {}'.format(set_name))

                # add data to the **raw** file
                self.store_data_source(fileh5, data[set_name], set_name)

                 # add data to the **default** file
                self.store_data_default(fileh5, data[set_name], set_name)

        # close file
        fileh5.close()

        # return information of the task + cache file
        return file_name


    def run(self):
        """
        Run task processing.
        """
        return self.process_metadata()


class DetectionNoSourceGrp(Detection):
    """ Caltech Pedestrian detection (default grp only - no source group) task class """

    # metadata filename
    filename_h5 = 'detection_d'

    def add_data_to_source(self, handler, data, set_name):
        """
        Dummy method
        """
        # do nothing


#---------------------------------------------------------
# Caltech 10x
#---------------------------------------------------------


class Detection10x(Detection):
    """ Caltech Pedestrian detection (10x data) preprocessing functions """

    skip_step = 3
    filename_h5 = 'detection_10x'


class Detection10xNoSourceGrp(Detection10x):
    """ Caltech Pedestrian detection (default grp only - no source group) task class """

    # metadata filename
    filename_h5 = 'detection_10x_d'

    def add_data_to_source(self, handler, data, set_name):
        """
        Dummy method
        """
        # do nothing


#---------------------------------------------------------
# Caltech 30x
#---------------------------------------------------------


class Detection30x(Detection):
    """ Caltech Pedestrian detection (30x data) preprocessing functions """

    skip_step = 1
    filename_h5 = 'detection_30x'


class Detection30xNoSourceGrp(Detection30x):
    """ Caltech Pedestrian detection (default grp only - no source group) task class """

    # metadata filename
    filename_h5 = 'detection_30x_d'

    def add_data_to_source(self, handler, data, set_name):
        """
        Dummy method
        """
        # do nothing
#!/usr/bin/env python
#

import argparse
import logging
from tqdm import tqdm
from clearml import Task
from clearml import Dataset
# from clearml import StorageManager
from wakepy import keepawake
import process
import train


def main(_args, loglevel):
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)

    with keepawake(keep_screen_awake=False):
        task = Task.init(project_name='Footfall', task_name='process and train')

        _, source_annotations_path, _, _ = process.get_paths(args)
        dataset = create_dataset(source_annotations_path)

        # Process images
        process.main(args, loglevel)

        # train new model
        dest_models_dir = train.main(args, loglevel)
        dataset.add_files(dest_models_dir)
        dataset.upload()
        dataset.finalize()


# Create a dataset with ClearML`s Dataset class
def create_dataset(source_annotations_path):
    dataset = Dataset.create(
        dataset_project="Footfall", dataset_name="heads"
    )
    dataset.add_files(path=source_annotations_path, recursive=True)
    dataset.upload()
    return dataset


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process images and train model")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-d", "--data_repo", default="az-datasets", help="repository where annotation data are located")
    parser.add_argument("-a", "--annotations_dir", default="annotations",
                        help="directory relative to this file where annotations are stored")
    parser.add_argument("-b", "--annotations_batch", default="2023-05-11-07_55_46-rgb-depth-fg_mask",
                        help="annotations subdir name (batch of images)")
    parser.add_argument("-l", "--labels_dir", default="labels", help="sub-directory of annotations where labels are")
    parser.add_argument("-i", "--images_dir", default="images", help="training images dir name")
    parser.add_argument("-s", "--img_filename_suffix", default="-rgb.jpg", help="suffix of file name to include as source images")
    parser.add_argument("-t", "--training_dir", default="training", help="Directory where training (output) folder is located")
    parser.add_argument("-r", "--transformation_name", default="rgb", help="Possible transformations: rgb, bw")

    parser.add_argument("-m", "--models_dir", default="models", help="Directory where models are located")
    parser.add_argument("-n", "--model_name", default="heads", help="Name of model. Folder name where result will be stored.")
    parser.add_argument("-e", "--epochs", default=300, help="Number of epochs to train")
    parser.add_argument("-x", "--validate", help="Validate best result of training", action='store_true')

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    main(args, loglevel)

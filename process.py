#!/usr/bin/env python
#

import argparse
import logging
import os
import pathlib
import shutil
import cv2
from tqdm import tqdm

_training_destinations = ['train', 'valid', 'test']


def main(args, loglevel):
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)

    annotations_repo_path, source_annotations_path, source_labels_path, training_path = get_paths(args)
    logging.info(f"Source images path: {source_annotations_path}")
    logging.info(f"Source labels path: {source_labels_path}")
    logging.info(f'Transformation name: {args.transformation_name}')

    # Delete and create destination training directories
    for dest in _training_destinations:
        shutil.rmtree(os.path.join(training_path, dest))
        os.makedirs(os.path.join(training_path, dest, args.labels_dir), exist_ok=True)
        os.makedirs(os.path.join(training_path, dest, args.images_dir), exist_ok=True)
    logging.info(f"Training path: {training_path}")

    logging.info("Copying...")
    source_images = [file_path
                     for file_path
                     in os.listdir(source_annotations_path)
                     if file_path.endswith(args.img_filename_suffix)]

    processed_images = []
    for file_path in tqdm(source_images, desc="Processing..."):
        processed_images.append(for_each_image(file_path, source_annotations_path, source_labels_path, training_path, args.images_dir, args.transformation_name,  args.labels_dir))

    logging.info(f"Images to be processed (suffix: '{args.img_filename_suffix}'): {len(source_images)}")
    logging.info(f"Image not found: {len([x for x in processed_images if x.get('r') == 'image not found'])}")
    logging.info(f"Label not found: {len([x for x in processed_images if x.get('r') == 'label not found'])}")
    logging.info(f"Label contains annotations: {len([x for x in processed_images if x.get('r') == 'annotations found'])}")
    logging.info(f"Destination train: {len([x for x in processed_images if x.get('dest') == 'train'])}")
    logging.info(f"Destination valid: {len([x for x in processed_images if x.get('dest') == 'valid'])}")
    logging.info(f"Destination test: {len([x for x in processed_images if x.get('dest') == 'test'])}")


def get_paths(args):
    annotations_repo_path = os.path.join(str(pathlib.Path(__file__).parent.resolve().parent),  # parent dir
                                         args.data_repo)
    source_annotations_path = os.path.join(annotations_repo_path,
                                           args.annotations_dir,
                                           args.annotations_batch)
    source_labels_path = os.path.join(source_annotations_path, args.labels_dir)
    training_path = os.path.join(annotations_repo_path, args.training_dir)
    return (annotations_repo_path, source_annotations_path, source_labels_path, training_path)


def for_each_image(img_file_name, source_images_path, source_labels_path, training_dir, images_dir, transformation_name,  labels_dir):
    # Get image
    img_file_path = os.path.join(source_images_path, img_file_name)
    if os.path.isfile(img_file_path) is False:
        logging.warning(f"Image {img_file_name} does not exists.")
        return {'r': "image not found"}

    # Find corresponding label
    label_filename = img_file_name.split('.')[0] + '.txt'
    label_file_path = os.path.join(source_labels_path, label_filename)
    if os.path.isfile(label_file_path) is False:
        return {'r': "label not found"}

    # Find destination for image
    destination = where_to_go(img_file_name)

    # Copy image to destination
    process_image(img_file_path, os.path.join(training_dir, destination, images_dir), img_file_name, transformation_name)

    # Copy label to destination
    process_label(label_file_path, os.path.join(training_dir, destination, labels_dir))

    return {'r': "annotations found", 'dest': destination}


def process_image(src_filepath, dest_dir, filename, transformation_name):
    if transformation_name == 'rgb':
        _ = shutil.copy2(src_filepath, dest_dir)

    if transformation_name == 'bw':
        image = cv2.imread(src_filepath)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(os.path.join(dest_dir, filename), gray)


# Parse and create label
def process_label(src, dest):
    _ = shutil.copy2(src, dest)
    src_file = open(src, 'r')
    label_file_name = src.split("\\")[-1]
    with open(os.path.join(dest, label_file_name), 'w') as dst_file:
        for src_line in src_file.readlines():
            cls_index, x1, y1, width, height = src_line.split()
            #if float(height) > 0.4:
            #    logging.warn(label_file_path)
            dst_file.write(f"{cls_index} {x1} {y1} {width} {height}\n")


# Find destination for image
def where_to_go(img_file_name):
    destiny_number = hash(img_file_name) % 100
    if destiny_number in range(0, 10):
        return _training_destinations[2]
    if destiny_number in range(11, 30):
        return _training_destinations[1]
    return _training_destinations[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split images in folders for training")
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
    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    main(args, loglevel)

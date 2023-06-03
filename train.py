#!/usr/bin/env python
#

import argparse
import logging
import os
import pathlib
from ultralytics import YOLO
import torch
from wakepy import keepawake
import shutil
from datetime import datetime

best_file_name = "best.pt"


def main(args, loglevel):
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)

    datasets_repo = os.path.join(pathlib.Path(__file__).parent.resolve().parent, 'az-datasets')
    todays_model_name = f'{args.model_name}{datetime.now().strftime("%Y-%m-%d_%H-%M")}'
    output_model_filepath = os.path.join(pathlib.Path(__file__).parent.resolve(), f"runs\\detect\\{todays_model_name}")
    training_dir = os.path.join(datasets_repo, args.training_dir)
    dest_models_dir = os.path.join(datasets_repo, args.models_dir, todays_model_name)
    logging.info(f"Training path: {training_dir}")

    logging.info(f"CUDA is available: {torch.cuda.is_available()}")
    logging.info(f"CUDA device count: {torch.cuda.device_count()}")

    # if torch.cuda.is_available() == False:
    #     return

    # Load the model.
    model = YOLO(os.path.join(datasets_repo, 'models', best_file_name))
    training_yaml_filepath = os.path.join(training_dir, 'data.yaml')

    # Training.
    with keepawake(keep_screen_awake=False):
        if args.validate:
            _ = model.val(data=training_yaml_filepath)
        else:
            _ = model.train(
                data=training_yaml_filepath,
                imgsz=416,
                epochs=int(args.epochs),
                batch=8,
                name=todays_model_name)
            _ = shutil.copy2(output_model_filepath, dest_models_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Train NN")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-t", "--training_dir", default="training", help="Directory where training (output) folder is located")
    parser.add_argument("-m", "--models_dir", default="models", help="Directory where models are located")
    parser.add_argument("-n", "--model_name", default="heads", help="Name of model. Folder name where result will be stored.")
    parser.add_argument("-e", "--epochs", default=300, help="Number of epochs to train")
    parser.add_argument("-a", "--validate", help="Validate best result of training", action='store_true')

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    main(args, loglevel)

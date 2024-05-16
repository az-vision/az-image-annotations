#!/usr/bin/env python
#

import argparse
import logging
import os
from ultralytics import YOLO
import torch
from wakepy import keepawake
from datetime import datetime


best_file_name = "best.pt"


def main(args, loglevel):
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)

    todays_model_name = f'{args.model_name}-{datetime.now().strftime("%Y-%m-%d_%H-%M")}'
    training_dir = os.path.join("C:\\azvision", args.training_dir)

    logging.info(f"Training path: {training_dir}")
    logging.info(f"CUDA is available: {torch.cuda.is_available()}")
    logging.info(f"CUDA device count: {torch.cuda.device_count()}")

    if torch.cuda.is_available() is False:
        return

    # Load the model.
    model = YOLO(args.src_model_filepath)
    training_yaml_filepath = os.path.join(training_dir, 'data.yaml')

    # Training.
    with keepawake(keep_screen_awake=False):
        if args.validate:
            _ = model.val(data=training_yaml_filepath)
        else:
            _ = model.train(
                data=training_yaml_filepath,
                epochs=int(args.epochs),
                patience=0,
                batch=-1,
                imgsz=640,
                save=True,
                cache=True,
                device=0,
                project="runs",
                name=todays_model_name,
                pretrained=True,
                resume=False,
                fraction=1.0,
                box=7,  # default is 7.5
                plots=True
            )

    # convert to  http://tools.luxonis.com/
    # RVC2, 5 shaves, use open VINO 2021.4 = false
    # https://github.com/luxonis/tools/blob/master/main.py


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Train NN")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-s", "--src_model_filepath", default="C:\\azvision\\trainer\\models\\best.pt", help="Source model filepath.")
    parser.add_argument("-t", "--training_dir", default="training", help="Directory where training (output) folder is located")
    parser.add_argument("-n", "--model_name", default="az-footfall", help="Name of model. Folder name where result will be stored.")
    parser.add_argument("-e", "--epochs", default=1, help="Number of epochs to train")
    parser.add_argument("-a", "--validate", help="Validate best result of training", action='store_true')

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    main(args, loglevel)

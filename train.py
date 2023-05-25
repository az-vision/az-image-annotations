#!/usr/bin/env python
#

import argparse
import logging
import os
import pathlib
from ultralytics import YOLO
import torch
from wakepy import keepawake


def main(args, loglevel):
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)

    training_dir = os.path.join(pathlib.Path(__file__).parent.resolve(), args.training_dir)
    logging.info(f"Training path: {training_dir}")
    
    logging.info(f"CUDA is available: {torch.cuda.is_available()}")
    logging.info(f"CUDA device count: {torch.cuda.device_count()}")

    if torch.cuda.is_available() == False:
        return


    # Load the model.
    model = YOLO('models/best.pt')

    # Training.
    with keepawake(keep_screen_awake=False):
        _ = model.train(
            data=os.path.join(training_dir, 'data.yaml'),
            imgsz=416,
            epochs=args.epochs,
            batch=8,
            name='heads_trained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Train NN")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-t", "--training_dir", default="training", help="Directory where training (output) folder is located")
    parser.add_argument("-e", "--epochs", default=100, help="Number of epochs to train")

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    main(args, loglevel)

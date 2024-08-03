from autodistill_grounding_dino import GroundingDINO
from autodistill.detection import CaptionOntology
import supervision as sv
import os
import cv2
from tqdm import tqdm

def convert_to_yolo_format(box, img_width, img_height):
    """
    Convert bounding box to YOLO format.

    Parameters:
    - box: A list or tuple containing [xmin, ymin, xmax, ymax].
    - img_width: Width of the image.
    - img_height: Height of the image.

    Returns:
    - A list containing [class, center_x, center_y, width, height] in YOLO format.
    """
    class_id = 0  # Since we're only detecting "animal", its class id can be 0.
    xmin, ymin, xmax, ymax = box
    center_x = (xmin + xmax) / 2.0 / img_width
    center_y = (ymin + ymax) / 2.0 / img_height
    width = (xmax - xmin) / img_width
    height = (ymax - ymin) / img_height

    return [class_id, center_x, center_y, width, height]


base_model = GroundingDINO(ontology=CaptionOntology({"animal": "animal"}))

batches_path = "C:\\azvision\\batches"

# Create the labels directory if it doesn't exist

for batch_name in os.listdir(batches_path):
    LABEL_PATH = os.path.join(batches_path, batch_name, "labels")
    os.makedirs(LABEL_PATH, exist_ok=True)
    # Iterate over all files in the IMAGE_PATH directory
    for image_name in tqdm(os.listdir(os.path.join(batches_path, batch_name)), desc=f"Processing images {batch_name}"):
        # Construct the full path to the image
        image_path = os.path.join(batches_path, batch_name, image_name)

        # Ensure the file is an image (you can add more file extensions if needed)
        if image_name.lower().endswith(('.jpg')):
            # Predict
            predictions = base_model.predict(image_path)

            # Read the image using OpenCV
            image = cv2.imread(image_path)
            img_height, img_width, _ = image.shape

            # Convert predictions to YOLO format
            yolo_annotations = []
            for pred in predictions:
                box = pred[0]  # Extracting the bounding box coordinates from the tuple
                yolo_annotation = convert_to_yolo_format(box, img_width, img_height)
                yolo_annotations.append(yolo_annotation)

            # Save annotations to a txt file
            label_file_path = os.path.join(LABEL_PATH, os.path.splitext(image_name)[0] + ".txt")
            with open(label_file_path, "w") as f:
                for annotation in yolo_annotations:
                    f.write(" ".join(map(str, annotation)) + "\n")

            # # Annotate the image
            # annotator = sv.RoundBoxAnnotator()
            # annotated_image = annotator.annotate(scene=image, detections=predictions,)

            # # Display the annotated image using OpenCV (optional)
            # cv2.imshow('Annotated Image', annotated_image)
            # cv2.waitKey(1000)
            # cv2.destroyAllWindows()

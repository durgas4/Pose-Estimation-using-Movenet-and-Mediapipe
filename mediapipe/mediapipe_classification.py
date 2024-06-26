# -*- coding: utf-8 -*-
"""mediapipe - classification

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1gXM6l8U8tuMb68LpagcJiDv06MLq3Qtg
"""

!pip install mediapipe

from google.colab import drive

# This will prompt for authorization.
drive.mount('/content/drive')

import os
import csv
import tempfile
import tensorflow as tf
import numpy as np
import cv2
import pandas as pd
import mediapipe as mp
from mediapipe.python.solutions import pose as mp_pose
# Initialize MediaPipe drawing module
mp_drawing = mp.solutions.drawing_utils

class MediapipePreprocessor(object):
    def __init__(self, images_in_folder, images_out_folder, csvs_out_path):
        self._images_in_folder = images_in_folder
        self._images_out_folder = images_out_folder
        self._csvs_out_path = csvs_out_path
        self._messages = []

        # Create a temp dir to store the pose CSVs per class
        self._csvs_out_folder_per_class = tempfile.mkdtemp()

        # Get list of pose classes and print image statistics
        self._pose_class_names = sorted(
            [n for n in os.listdir(self._images_in_folder) if not n.startswith('.')])

    def process(self, per_pose_class_limit=None, detection_threshold=0.1):
        pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=detection_threshold)

        for pose_class_name in self._pose_class_names:
            print('Preprocessing', pose_class_name)

            # Paths for the pose class.
            images_in_folder = os.path.join(self._images_in_folder, pose_class_name)
            images_out_folder = os.path.join(self._images_out_folder, pose_class_name)
            csv_out_path = os.path.join(self._csvs_out_folder_per_class, pose_class_name + '.csv')
            if not os.path.exists(images_out_folder):
                os.makedirs(images_out_folder)

            # Detect landmarks in each image and write them to a CSV file
            with open(csv_out_path, 'w') as csv_out_file:
                csv_out_writer = csv.writer(csv_out_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
                # Get list of images
                image_names = sorted([n for n in os.listdir(images_in_folder) if not n.startswith('.')])
                if per_pose_class_limit is not None:
                    image_names = image_names[:per_pose_class_limit]

                valid_image_count = 0

                # Detect pose landmarks from each image
                for image_name in image_names:
                    image_path = os.path.join(images_in_folder, image_name)

                    try:
                        image = cv2.imread(image_path)
                        image_height, image_width, _ = image.shape
                    except:
                        self._messages.append(f'Skipped {image_path}. Invalid image.')
                        continue

                    # Convert image to RGB format
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                    # Run pose estimation on the image
                    results = pose.process(image_rgb)

                    # Check if landmarks were detected
                    if not results.pose_landmarks:
                        self._messages.append(f'Skipped {image_path}. No pose was confidently detected.')
                        continue

                    valid_image_count += 1

                    # Draw the pose landmarks on the image for debugging
                    mp_drawing.draw_landmarks(
                        image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

                    # Write the processed image to the output folder
                    cv2.imwrite(os.path.join(images_out_folder, image_name), image)

                    # Get the landmark coordinates and write them to the CSV file
                    pose_landmarks = np.array([[lm.x * image_width, lm.y * image_height, lm.z] for lm in results.pose_landmarks.landmark], dtype=np.float32)
                    coordinates = pose_landmarks.flatten().astype(np.str).tolist()
                    csv_out_writer.writerow([image_name] + coordinates)

                if not valid_image_count:
                    raise RuntimeError(f'No valid images found for the "{pose_class_name}" class.')

        # Print the error messages collected during preprocessing.
        print('\n'.join(self._messages))

        # Combine all per-class CSVs into a single output file
        all_landmarks_df = self._all_landmarks_as_dataframe()
        all_landmarks_df.to_csv(self._csvs_out_path, index=False)

    def class_names(self):
        """List of classes found in the training dataset."""
        return self._pose_class_names

    def _all_landmarks_as_dataframe(self):
        """Merge all per-class CSVs into a single dataframe."""
        total_df = None
        for class_index, class_name in enumerate(self._pose_class_names):
            csv_out_path = os.path.join(self._csvs_out_folder_per_class, class_name + '.csv')
            per_class_df = pd.read_csv(csv_out_path, header=None)

            # Add the labels
            per_class_df['class_no'] = [class_index] * len(per_class_df)
            per_class_df['class_name'] = [class_name] * len(per_class_df)

            # Append the folder name to the filename column (first column)
            per_class_df[per_class_df.columns[0]] = (os.path.join(class_name, '') +
                                                     per_class_df[per_class_df.columns[0]].astype(str))

            if total_df is None:
                # For the first class, assign its data to the total dataframe
                total_df = per_class_df
            else:
                # Concatenate each class's data into the total dataframe
                total_df = pd.concat([total_df, per_class_df], axis=0)

        list_name = [[f'{bodypart}_x', f'{bodypart}_y', f'{bodypart}_score'] for bodypart in mp_pose.PoseLandmark]
        header_name = []
        for columns_name in list_name:
            header_name += columns_name
        header_name = ['file_name'] + header_name
        header_map = {total_df.columns[i]: header_name[i] for i in range(len(header_name))}
        total_df.rename(header_map, axis=1, inplace=True)

        return total_df

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
df = pd.read_excel('/content/drive/MyDrive/final project/sit-stand/annotate.xlsx')


# Split the data into training and testing sets (80-20 split)
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

# Save the split data into separate XLSX files
train_df.to_csv('train_data.csv', index=False)
test_df.to_csv('test_data.csv', index=False)

import os
import random
import shutil

def split_into_train_test(images_origin, images_dest, test_split):
  _, dirs, _ = next(os.walk(images_origin))

  TRAIN_DIR = os.path.join(images_dest, 'train')
  TEST_DIR = os.path.join(images_dest, 'test')
  os.makedirs(TRAIN_DIR, exist_ok=True)
  os.makedirs(TEST_DIR, exist_ok=True)

  for dir in dirs:
    # Get all filenames for this dir, filtered by filetype
    filenames = os.listdir(os.path.join(images_origin, dir))
    filenames = [os.path.join(images_origin, dir, f) for f in filenames if (
        f.endswith('.png') or f.endswith('.jpg') or f.endswith('.jpeg') or f.endswith('.bmp'))]
    # Shuffle the files, deterministically
    filenames.sort()
    random.seed(42)
    random.shuffle(filenames)
    # Divide them into train/test dirs
    os.makedirs(os.path.join(TEST_DIR, dir), exist_ok=True)
    os.makedirs(os.path.join(TRAIN_DIR, dir), exist_ok=True)
    test_count = int(len(filenames) * test_split)
    for i, file in enumerate(filenames):
      if i < test_count:
        destination = os.path.join(TEST_DIR, dir, os.path.split(file)[1])
      else:
        destination = os.path.join(TRAIN_DIR, dir, os.path.split(file)[1])
      shutil.copyfile(file, destination)
    print(f'Moved {test_count} of {len(filenames)} from class "{dir}" into test.')
  print(f'Your split dataset is in "{images_dest}"')

dataset_in = '/content/drive/MyDrive/final project/sit-stand'

 # You can leave the rest alone:
if not os.path.isdir(dataset_in):
  raise Exception("dataset_in is not a valid directory")
else:
  dataset_out = 'split_' + dataset_in
  split_into_train_test(dataset_in, dataset_out, test_split=0.2)
  IMAGES_ROOT = dataset_out

IMAGES_ROOT = '/content/split_/content/drive/MyDrive/final project/sit-stand'

# Define paths for input data
images_in_train_folder = os.path.join(IMAGES_ROOT, 'train')

images_out_train_folder = 'pose_images_out_train'
csvs_out_train_path = 'train_data.csv'

# Initialize and run the preprocessor for training data
preprocessor_train = MediapipePreprocessor(
    images_in_folder=images_in_train_folder,
    images_out_folder=images_out_train_folder,
    csvs_out_path=csvs_out_train_path
)

preprocessor_train.process(per_pose_class_limit=None)

import tqdm
#IMAGES_ROOT = '/content/split_/content/sit-stand'
# Define paths for test data
import os
import sys
images_in_test_folder = os.path.join(IMAGES_ROOT, 'test')
images_out_test_folder = 'pose_images_out_test'
csvs_out_test_path = 'test_data.csv'

# Initialize and run the preprocessor for test data
preprocessor_test = MediapipePreprocessor(
    images_in_folder=images_in_test_folder,
    images_out_folder=images_out_test_folder,
    csvs_out_path=csvs_out_test_path
)

preprocessor_test.process(per_pose_class_limit=None)

csvs_out_train_path = 'train_data.csv'
csvs_out_test_path = 'test_data.csv'

def load_pose_landmarks(csv_path):
  # Load the CSV file
  dataframe = pd.read_csv(csv_path)
  df_to_process = dataframe.copy()

  # Drop the file_name columns as you don't need it during training.
  df_to_process.drop(columns=['file_name'], inplace=True)

  # Extract the list of class names
  classes = df_to_process.pop('class_name').unique()

  # Extract the labels
  y = df_to_process.pop('class_no')

  # Convert the input features and labels into the correct format for training.
  X = df_to_process.astype('float64')
  y = keras.utils.to_categorical(y)

  return X, y, classes, dataframe

from tensorflow import keras
# Load the train data
X, y, class_names, _ = load_pose_landmarks(csvs_out_train_path)

# Split training data (X, y) into (X_train, y_train) and (X_val, y_val)

X_train, X_val, y_train, y_val = train_test_split(X, y,
                                                  test_size=0.15)

# Load the test data
X_test, y_test, _, df_test = load_pose_landmarks(csvs_out_test_path)

import tensorflow as tf
from tensorflow import keras

# Define the BodyPart enum (you might need to import this from your specific MediaPipe library)
class BodyPart:
  NOSE=0
  LEFT_EYE_INNER=1
  LEFT_EYE=2
  LEFT_EYE_OUTER=3
  RIGHT_EYE_INNER=4
  RIGHT_EYE=5
  RIGHT_EYE_OUTER=6
  LEFT_EAR=7
  RIGHT_EAR=8
  MOUTH_LEFT=9
  MOUTH_RIGHT=10
  LEFT_SHOULDER=11
  RIGHT_SHOULDER=12
  LEFT_ELBOW=13
  RIGHT_ELBOW=14
  LEFT_WRIST=15
  RIGHT_WRIST=16
  LEFT_PINKY=17
  RIGHT_PINKY=18
  LEFT_INDEX=19
  RIGHT_INDEX=20
  LEFT_THUMB=21
  RIGHT_THUMB=22
  LEFT_HIP=23
  RIGHT_HIP=24
  LEFT_KNEE=25
  RIGHT_KNEE=26
  LEFT_ANKLE=27
  RIGHT_ANKLE=28
  LEFT_HEEL=29
  RIGHT_HEEL=30
  LEFT_FOOT_INDEX=31
  RIGHT_FOOT_INDEX=32

 # Add more body parts as needed

def get_center_point(landmarks, left_bodypart, right_bodypart):
    """Calculates the center point of the two given landmarks."""
    left = tf.gather(landmarks, left_bodypart, axis=1)
    right = tf.gather(landmarks, right_bodypart, axis=1)
    center = left * 0.5 + right * 0.5
    return center

def get_pose_size(landmarks, torso_size_multiplier=2.5):
    """Calculates pose size."""
    # Hips center
    hips_center = get_center_point(landmarks, BodyPart.LEFT_HIP, BodyPart.RIGHT_HIP)

    # Shoulders center
    shoulders_center = get_center_point(landmarks, BodyPart.LEFT_SHOULDER, BodyPart.RIGHT_SHOULDER)

    # Torso size as the minimum body size
    torso_size = tf.linalg.norm(shoulders_center - hips_center)

    # Pose center
    pose_center_new = get_center_point(landmarks, BodyPart.LEFT_HIP, BodyPart.RIGHT_HIP)
    pose_center_new = tf.expand_dims(pose_center_new, axis=1)

    # Dist to pose center
    d = tf.gather(landmarks - pose_center_new, 0, axis=0)
    # Max dist to pose center
    max_dist = tf.reduce_max(tf.linalg.norm(d, axis=0))

    # Normalize scale
    pose_size = tf.maximum(torso_size * torso_size_multiplier, max_dist)

    return pose_size

def normalize_pose_landmarks(landmarks):
    """Normalizes the landmarks translation and scales to a constant pose size."""
    # Move landmarks so that the pose center becomes (0,0)
    pose_center = get_center_point(landmarks, BodyPart.LEFT_HIP, BodyPart.RIGHT_HIP)
    pose_center = tf.expand_dims(pose_center, axis=1)
    landmarks = landmarks - pose_center

    # Scale the landmarks to a constant pose size
    pose_size = get_pose_size(landmarks)
    landmarks /= pose_size

    return landmarks

def landmarks_to_embedding(landmarks_and_scores):
    """Converts the input landmarks into a pose embedding."""
    # Reshape the flat input into a matrix with shape=(33, 3)
    reshaped_inputs = keras.layers.Reshape((33, 3))(landmarks_and_scores)

    # Normalize landmarks 2D
    landmarks = normalize_pose_landmarks(reshaped_inputs[:, :, :2])

    # Flatten the normalized landmark coordinates into a vector
    embedding = keras.layers.Flatten()(landmarks)

    return embedding

import tensorflow as tf
from tensorflow import keras

# Define the model
class CustomModel(tf.keras.Model):
    def __init__(self, input_shape=(99), num_classes=None):
        super(CustomModel, self).__init__()

        self.embedding = landmarks_to_embedding
        self.dense1 = keras.layers.Dense(128, activation=tf.nn.relu6)
        self.dropout1 = keras.layers.Dropout(0.5)
        self.dense2 = keras.layers.Dense(64, activation=tf.nn.relu6)
        self.dropout2 = keras.layers.Dropout(0.5)
        self.outputs = keras.layers.Dense(num_classes, activation="softmax")

    def call(self, inputs):
        x = self.embedding(inputs)
        x = self.dense1(x)
        x = self.dropout1(x)
        x = self.dense2(x)
        x = self.dropout2(x)
        x = self.outputs(x)
        return x

# Create an instance of the custom model
model = CustomModel(input_shape=(99), num_classes=len(class_names))

# Display a clean model summary without custom TensorFlow operations
model.build(input_shape=(None, 99))
model.summary()

y_train.shape
y_val.shape

# Compile the model
model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# validation accuracy.
checkpoint_path = "saved_model"
checkpoint = keras.callbacks.ModelCheckpoint(checkpoint_path,
                             monitor='val_accuracy',
                             verbose=1,
                             save_best_only=True,
                             mode='max')
earlystopping = keras.callbacks.EarlyStopping(monitor='val_accuracy',
                                              patience=20)

# Start training
history = model.fit(X_train, y_train,
                    epochs=200,
                    batch_size=16,
                    validation_data=(X_val, y_val),
                    callbacks=[checkpoint, earlystopping])

# Save the model in the SavedModel format
model.save("custom_model_saved_model")

# Visualize the training history to see whether you're overfitting.
import matplotlib.pyplot as plt
plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title('Model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['TRAIN', 'VAL'], loc='lower right')
plt.show()

# Visualize the training history to see whether you're overfitting.
plt.plot(history.history['val_loss'])
plt.plot(history.history['loss'])
plt.title('Model Loss')
plt.ylabel('Loss')
plt.xlabel('epoch')
plt.legend(['TRAIN', 'VAL'], loc='lower right')
plt.show()

# Evaluate the model using the TEST dataset
loss, accuracy = model.evaluate(X_test, y_test)

predictions = model.predict(X_test)

X_test

max_indices = [np.argmax(internal_array) for internal_array in predictions]

print([(i, df_test['file_name'][i], class_names[val]) for i, val in enumerate(max_indices)])

import itertools
def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues):
  """Plots the confusion matrix."""
  if normalize:
    cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    print("Normalized confusion matrix")
  else:
    print('Confusion matrix, without normalization')

  plt.imshow(cm, interpolation='nearest', cmap=cmap)
  plt.title(title)
  plt.colorbar()
  tick_marks = np.arange(len(classes))
  plt.xticks(tick_marks, classes, rotation=55)
  plt.yticks(tick_marks, classes)
  fmt = '.2f' if normalize else 'd'
  thresh = cm.max() / 2.
  for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
    plt.text(j, i, format(cm[i, j], fmt),
              horizontalalignment="center",
              color="white" if cm[i, j] > thresh else "black")

  plt.ylabel('True label')
  plt.xlabel('Predicted label')
  plt.tight_layout()

# Classify pose in the TEST dataset using the trained model
y_pred = model.predict(X_test)

# Convert the prediction result to class name
y_pred_label = [class_names[i] for i in np.argmax(y_pred, axis=1)]
y_true_label = [class_names[i] for i in np.argmax(y_test, axis=1)]

# Plot the confusion matrix
cm = confusion_matrix(np.argmax(y_test, axis=1), np.argmax(y_pred, axis=1))
plot_confusion_matrix(cm,
                      class_names,
                      title ='Confusion Matrix of Pose Classification Model')

# Print the classification report
print('\nClassification Report:\n', classification_report(y_true_label,
                                                          y_pred_label))

# Commented out IPython magic to ensure Python compatibility.
# ouput predicted images

IMAGE_PER_ROW = 3
MAX_NO_OF_IMAGE_TO_PLOT = 10

# Extract the list of correctly predicted poses
true_predict = [id_in_df for id_in_df in range(len(y_test)) \
                if y_pred_label[id_in_df] == y_true_label[id_in_df]]
if len(true_predict) > MAX_NO_OF_IMAGE_TO_PLOT:
  true_predict = true_predict[:MAX_NO_OF_IMAGE_TO_PLOT]

# Plot the correctly predicted images
row_count = len(true_predict) // IMAGE_PER_ROW + 1
fig = plt.figure(figsize=(10 * IMAGE_PER_ROW, 10 * row_count))
for i, id_in_df in enumerate(true_predict):
  ax = fig.add_subplot(row_count, IMAGE_PER_ROW, i + 1)
  image_path = os.path.join(images_out_test_folder,
                            df_test.iloc[id_in_df]['file_name'])

  image = cv2.imread(image_path)
  plt.title("Predict: %s; Actual: %s"
#             % (y_pred_label[id_in_df], y_true_label[id_in_df]))
  plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
plt.show()

converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

print('Model size: %dKB' % (len(tflite_model) / 1024))

with open('pose_classifier.tflite', 'wb') as f:
  f.write(tflite_model)

with open('pose_labels.txt', 'w') as f:
  f.write('\n'.join(class_names))

def evaluate_model(interpreter, X, y_true):
  """Evaluates the given TFLite model and return its accuracy."""
  input_index = interpreter.get_input_details()[0]["index"]
  output_index = interpreter.get_output_details()[0]["index"]

  # Run predictions on all given poses.
  y_pred = []
  for i in range(len(y_true)):
    # Pre-processing: add batch dimension and convert to float32 to match with
    # the model's input data format.
    test_image = X[i: i + 1].astype('float32')
    interpreter.set_tensor(input_index, test_image)

    # Run inference.
    interpreter.invoke()

    # Post-processing: remove batch dimension and find the class with highest
    # probability.
    output = interpreter.tensor(output_index)
    predicted_label = np.argmax(output()[0])
    y_pred.append(predicted_label)

  # Compare prediction results with ground truth labels to calculate accuracy.
  y_pred = keras.utils.to_categorical(y_pred)
  return accuracy_score(y_true, y_pred)

# Evaluate the accuracy of the converted TFLite model
classifier_interpreter = tf.lite.Interpreter(model_content=tflite_model)
classifier_interpreter.allocate_tensors()
print('Accuracy of TFLite model: %s' %
      evaluate_model(classifier_interpreter, X_test, y_test))

!zip pose_classifier.zip pose_labels.txt pose_classifier.tflite

# Download the zip archive if running on Colab.
try:
  from google.colab import files
  files.download('pose_classifier.zip')
except:
  pass
# Prediction.py
# Imports
import os
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import pandas as pd

# Setting CUDA devices to not use GPU
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
tf.config.set_visible_devices([], 'GPU')

# Prediction Model Class
class PredictionModel:
    def __init__(self, MODEL_PATH, sequence_length=288, prediction_steps=12, min_val=-85.199997, max_val=38.400000):
        # Load TensorFlow model from specified path
        self.model = tf.saved_model.load(MODEL_PATH)
        # Retrieve the inference function from the loaded model
        self.infer = self.model.signatures['serving_default']
        # Set up model parameters
        self.sequence_length = sequence_length
        self.prediction_steps = prediction_steps
        # Initialize scaler with the min and max values from training for normalization
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.scaler.fit(np.array([[min_val], [max_val]]))
    
    # Function to normalize Sensor data as the model was trained using normalized values
    def normalize(self, data):
        # Reshape data for scaling
        if isinstance(data, pd.Series):
            data = data.values.reshape(-1, 1)
        elif isinstance(data, np.ndarray):
            data = data.reshape(-1, 1)
        return self.scaler.transform(data)
    
    # Function to create sequences from the sensor data for prediction
    def create_sequences(self, data):
        # Generate data sequences for model input
        sequences = []
        for i in range(self.sequence_length, len(data) - self.prediction_steps + 1):
            sequences.append(data[i - self.sequence_length:i])
        return np.array(sequences)

    # Function to predict using the trained TensorFlow model on reshaped input data
    def predict(self, reshaped_input):
        # Make predictions and transform the results back to the original scale
        predictions_normalized = self.infer(tf.constant(reshaped_input, dtype=tf.float32))['dense_1'].numpy()
        predictions = self.scaler.inverse_transform(predictions_normalized)
        # Print predictions for debugging and verification
        print(f"Predictions generated: {predictions.flatten()}")  
        return predictions.flatten()
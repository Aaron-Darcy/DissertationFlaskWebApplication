# Incorporating Machine Learning in a Microcontroller-Driven Sensor System for Monitoring Cold Chain Pharmaceutical Products

## Thesis Overview
This repository contains the code and documents for my thesis titled "Incorporating Machine Learning in a Microcontroller-Driven Sensor System for Monitoring Cold Chain Pharmaceutical Products." The project explores the integration of machine learning techniques with a microcontroller-based sensor system to enhance the monitoring of cold chain environments, particularly for pharmaceutical products that require strict temperature controls.

## Introduction
The pharmaceutical industry relies heavily on cold chain logistics to maintain the integrity of temperature-sensitive products. This thesis investigates how machine learning algorithms can be integrated into a microcontroller-driven sensor system to improve the accuracy and predictability of temperature monitoring, reducing the risk of product spoilage and ensuring patient safety.

## Project Structure
- `/src`: Contains the source code for the microcontroller firmware, web application, and machine learning models.
- `/data`: Includes datasets used for training and testing the machine learning models.
- `/models`: Saved models and scripts for loading and evaluating them.
- `/docs`: Documentation, including the thesis report and supplementary materials.
- `/tests`: Contains the test cases and scripts used to validate the system.

## System Requirements
### Software
- **Python 3.x**: Required for the machine learning and data processing scripts.
- **C++**: Used for programming the ESP32 microcontroller.
- **Google Colab**: Used for creating machine learning models & data analysis.
- **MySQL Workbench 8.0**: Used for data preprocessing and management.
- **Flask**: For building the web application.

### Hardware
- **ESP32 Microcontroller**
- **Ruuvi Tag Open Source BLE Sensor**

# Flask Application for Web Application Element of Dissertation

This application is designed to monitor temperature sensors and send alerts via email and SMS when certain thresholds are reached or predicted to be reached(via LSTM Model). It uses Flask for the backend, InfluxDB for timeseries data storage, and SendGrid and Twilio for notifications.

## Setup Instructions

### Requirements

- Python 3.x
- pip (Python package installer)
- Virtual environment (recommended)

### Installation

1. Clone the repository:
   git clone https://github.com/Aaron-Darcy/FinalYearDissertationWebApplication/
2. cd into root folder
3. Set up a virtual environment (optional but recommended):
   python -m venv venv
   .\venv\Scripts\activate
4. Install the required packages:
   pip install -r requirements.txt
5. Set up the `.env` file in root directory with configuration and secrets. Use the `.env.example` file as a template.

### Running the Application

1. To start the Flask server, run(when enviroment is enabled):
   flask run


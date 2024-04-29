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


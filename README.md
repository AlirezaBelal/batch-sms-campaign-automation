# Automated SMS Messaging System

This project is an automated SMS messaging system that sends personalized messages to a list of contacts from a CSV file
using the [SMS-Gate](https://api.sms-gate.app) API service.

## Features

- Sends personalized SMS messages to a list of contacts
- Automatically converts phone numbers to international format
- Advanced logging system for tracking the sending process
- Detailed reporting on successful and failed messages
- Robust error handling with helpful error messages

## Prerequisites

- Python 3.6 or higher
- Required Python packages listed in `requirements.txt`

## Installation and Setup

1. Clone the project:
   ```bash
   git clone https://github.com/yourusername/sms-project.git
   cd sms-project
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Linux/Mac
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Prepare your data:
    - Place your CSV file in the `data` folder
    - Make sure your CSV file contains `first_name_per` and `selected_phone` columns

5. Configuration:
    - Open `config.py` and review the API settings and CSV file path
    - Modify settings as needed for your environment

## Usage

To run the program, enter the following command:

```bash
python main.py
```

Logs will be stored in the `logs` folder and also displayed in the console output.

## CSV File Format

The CSV file must include at least two columns:

- `first_name_per`: Contact name used in the message
- `selected_phone`: Contact phone number

Example:

```
first_name_per,selected_phone
Ali,09123456789
Mohammad,09198765432
```

## Troubleshooting

If you encounter issues:

1. Check the log files in the `logs` folder
2. Verify that your API credentials are correct
3. Check your CSV file format
4. Verify your internet connection

## Development and Improvements

Consider these ideas for further development:

- Add a web or graphical user interface
- Support for more file formats (such as Excel)
- Create various message templates
- Add scheduled message sending functionality
- Implement advanced reporting system
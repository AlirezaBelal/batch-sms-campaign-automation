# Batch Messaging Delivery System

## Overview

This system sends structured SMS messages to a list of users using external API integration.

It focuses on:

* Batch message processing
* Phone number normalization
* Reliable delivery tracking
* Structured logging and reporting

---

## Core Features

### 1. Message Delivery Engine

* Sends personalized SMS messages
* Uses external SMS API
* Supports batch processing

### 2. Data Processing Layer

* Reads contacts from CSV files
* Normalizes phone numbers
* Prepares message payloads

### 3. Logging System

* Tracks successful sends
* Records failed deliveries
* Stores execution logs

---

## Processing Flow

Input CSV → Data Parsing → Normalization → Message Generation → API Delivery → Logging

---

## Project Structure

* main.py → entry point
* sms_service → delivery engine
* utils → helper functions
* config.py → configuration layer

---

## Requirements

* Python 3.6+
* requests library
* SMS API credentials

---

## Setup

1. Clone repository
   git clone [https://github.com/yourusername/sms-project.git](https://github.com/yourusername/sms-project.git)

2. Create virtual environment
   python -m venv venv

3. Activate environment
   source venv/bin/activate

4. Install dependencies
   pip install -r requirements.txt

5. Configure system
   Edit config.py for API settings and file paths

---

## Usage

python main.py

---

## Input Format

Required CSV columns:

* first_name_per
* selected_phone

---

## System Value

This project demonstrates:

* API integration architecture
* Batch processing pipeline
* Messaging delivery system design
* Logging and reliability handling


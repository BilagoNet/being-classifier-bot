# Being Classification Bot

A Telegram bot that collects and classifies information about different types of beings (Human/Animal/Alien) through a structured conversation flow and stores the data in both a Telegram group and Google Sheets.

## Features

- Three classification flows: Human, Animal, and Alien
- Structured data collection with validation
- Inline keyboard buttons with selection feedback
- Automatic data storage in Google Sheets with dual numbering system
- Posts results to a Telegram group
- Error handling and input validation
- Automatic sheet creation and headers setup

## Prerequisites

- Python 3.7+
- Google Cloud Project with Sheets API enabled
- Telegram Bot Token
- Google Sheets API credentials (Service Account)
- Telegram Group for posting results

## Installation

1. Clone the repository

2. Create and activate virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Create `.env` file with your credentials:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_GROUP_ID=your_group_id
   SPREADSHEET_ID=your_spreadsheet_id
   ```

2. Set up Google Sheets:
   - Create a new Google Cloud Project
   - Enable Google Sheets API
   - Create Service Account and download credentials
   - Save the service account credentials as `token.json`
   - Create a new Google Sheets document
   - Share the document with your service account email

## Data Structure

### Google Sheets Format
Three separate sheets are automatically created with the following columns:

1. Humans:
   - No. (Auto-increment line number starting from 1)
   - ID (Unique bot number starting from 10000)
   - Type
   - Gender
   - Age
   - Nationality
   - Education
   - Eye Color
   - Hair Color
   - Height
   - Date

2. Animals:
   - No. (Auto-increment line number starting from 1)
   - ID (Unique bot number starting from 10000)
   - Type
   - Species
   - Mammal
   - Predator
   - Color
   - Weight
   - Age
   - Date

3. Aliens:
   - No. (Auto-increment line number starting from 1)
   - ID (Unique bot number starting from 10000)
   - Type
   - Humanoid
   - Race (if humanoid)
   - Skin Color (if humanoid)
   - Dangerous (if humanoid)
   - Has Reason (if humanoid)
   - Weight (if humanoid)
   - Date

### Telegram Post Format
```
#[Unique Bot ID]
[Date]
Specie: [Human/Animal/Alien]
[Field 1]: [Value]
[Field 2]: [Value]
...
```

## Usage

1. Start the bot:
   ```bash
   python being_classifier_bot.py
   ```

2. In Telegram:
   - Start chat with bot: `/start`
   - Begin classification: `/classify`
   - Cancel anytime: `/cancel`

## Features Details

### Conversation Flow
- Interactive buttons for type selection
- Selection feedback in messages
- Structured data collection based on being type
- Validation for all inputs
- Auto-cancellation for non-humanoid aliens

### Data Validation
- Numeric values must be positive
- Gender must be Male/Female
- Alien race must be X, Y, or Z
- Required fields cannot be empty

### Error Handling
- Invalid input handling
- Google Sheets connection errors
- Telegram API errors
- Graceful error messages to users

### Numbering System
- Each entry has two numbers:
  1. Line number (No.): Sequential number starting from 1 for each sheet
  2. Unique ID: Unique identifier starting from 10000, shared across all sheets
- Telegram posts use the Unique ID for reference
- Both numbers auto-increment independently

## Development

The bot is built using:
- python-telegram-bot for Telegram integration
- Google Sheets API for data storage
- Environment variables for configuration
- Logging for error tracking
- Type hints and async/await patterns

## License

This project is licensed under the MIT License. 
# Standard library imports
import logging
import os
from datetime import datetime
from warnings import filterwarnings

# Third-party imports
from dotenv import load_dotenv

# Google Sheets API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Telegram API imports
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.warnings import PTBUserWarning


# Filter out warnings
filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handler
BEING_TYPE, HUMAN_FLOW, ANIMAL_FLOW, ALIEN_FLOW = range(4)

class BeingClassifierBot:
    def __init__(self):
        """Initialize bot with environment checks"""
        self.current_data = {}  # Store temporary data during classification
        
        # Check required environment variables
        self.check_env_variables()
        
        # Initialize Google Sheets connection
        self.initialize_sheets()
    
    def check_env_variables(self):
        """Check if all required environment variables are set"""
        required_vars = {
            'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
            'TELEGRAM_GROUP_ID': 'Telegram Group ID',
            'SPREADSHEET_ID': 'Google Spreadsheet ID'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{description} ({var})")
        
        if missing_vars:
            error_message = (
                "Missing required environment variables:\n"
                f"{chr(10).join('- ' + var for var in missing_vars)}\n\n"
                "Please create a .env file with the following variables:\n"
                "TELEGRAM_BOT_TOKEN=your_bot_token\n"
                "TELEGRAM_GROUP_ID=your_group_id\n"
                "SPREADSHEET_ID=your_spreadsheet_id"
            )
            logger.error(error_message)
            raise EnvironmentError(error_message)
            
    def initialize_sheets(self):
        """Initialize Google Sheets API connection"""
        try:
            if not os.path.exists('token.json'):
                error_message = (
                    "Google Sheets credentials file (token.json) not found.\n"
                    "Please follow the setup instructions in README.md to create and download your credentials."
                )
                logger.error(error_message)
                raise FileNotFoundError(error_message)
                
            credentials = service_account.Credentials.from_service_account_file(
                'token.json',
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            self.spreadsheet_id = os.getenv('SPREADSHEET_ID')
            
            # Verify spreadsheet access and create sheets if they don't exist
            self.verify_sheets()
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            raise Exception("Failed to initialize Google Sheets. Check your credentials and permissions.")
    
    def verify_sheets(self):
        """Verify sheets exist and create them if they don't"""
        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            existing_sheets = {sheet['properties']['title'] for sheet in spreadsheet['sheets']}
            required_sheets = {'Humans', 'Animals', 'Aliens'}
            
            # Create missing sheets
            for sheet_name in required_sheets - existing_sheets:
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': sheet_name,
                                    'gridProperties': {
                                        'rowCount': 1000,
                                        'columnCount': 20
                                    }
                                }
                            }
                        }]
                    }
                ).execute()
                
                # Add headers
                headers = [['No.', 'ID', 'Type']]
                if sheet_name == 'Humans':
                    headers[0].extend(['Gender', 'Age', 'Nationality', 'Education', 'Eye Color', 'Hair Color', 'Height', 'Date'])
                elif sheet_name == 'Animals':
                    headers[0].extend(['Species', 'Mammal', 'Predator', 'Color', 'Weight', 'Age', 'Date'])
                elif sheet_name == 'Aliens':
                    headers[0].extend(['Humanoid', 'Race', 'Skin Color', 'Dangerous', 'Has Reason', 'Weight', 'Date'])
                
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!A1',
                    valueInputOption='RAW',
                    body={'values': headers}
                ).execute()
                
        except Exception as e:
            logger.error(f"Failed to verify/create sheets: {e}")
            raise Exception("Failed to verify/create sheets. Check your spreadsheet permissions.")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the bot and show welcome message"""
        await update.message.reply_text(
            "Welcome to Being Classification Bot!\n"
            "Use /classify to start classifying a being."
        )
    
    async def start_classification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the classification process"""
        # Clear any existing data
        context.user_data.clear()
        
        keyboard = [
            [
                InlineKeyboardButton("Human", callback_data="Human"),
                InlineKeyboardButton("Animal", callback_data="Animal"),
                InlineKeyboardButton("Alien", callback_data="Alien")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("What type of being?", reply_markup=reply_markup)
        return BEING_TYPE
    
    async def process_being_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process the being type selection"""
        query = update.callback_query
        await query.answer()
        
        # Edit message to show selection
        await query.message.edit_text(
            f"What type of being?\nSelected: {query.data}"
        )
        
        being_type = query.data
        context.user_data['being_type'] = being_type
        context.user_data['data'] = {'type': being_type}
        
        if being_type == "Human":
            await query.message.reply_text("Please enter your gender (Male/Female):")
            context.user_data['current_field'] = 'gender'
            return HUMAN_FLOW
        elif being_type == "Animal":
            await query.message.reply_text("Please enter the species:")
            context.user_data['current_field'] = 'species'
            return ANIMAL_FLOW
        else:  # Alien
            keyboard = [
                [
                    InlineKeyboardButton("Yes", callback_data="Yes"),
                    InlineKeyboardButton("No", callback_data="No")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Is it humanoid?", reply_markup=reply_markup)
            return ALIEN_FLOW
    
    async def process_human_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process human classification flow"""
        if 'current_field' not in context.user_data:
            context.user_data['current_field'] = 'gender'
            
        text = update.message.text
        data = context.user_data.get('data', {})
        
        if context.user_data['current_field'] == 'gender':
            if text.lower() not in ['male', 'female']:
                await update.message.reply_text("Please enter either Male or Female:")
                return HUMAN_FLOW
            data['gender'] = text.capitalize()
            await update.message.reply_text("Enter age (numeric):")
            context.user_data['current_field'] = 'age'
            
        elif context.user_data['current_field'] == 'age':
            try:
                age = int(text)
                if age <= 0:
                    raise ValueError
                data['age'] = age
                await update.message.reply_text("Enter nationality:")
                context.user_data['current_field'] = 'nationality'
            except ValueError:
                await update.message.reply_text("Please enter a valid positive number for age:")
                return HUMAN_FLOW
                
        elif context.user_data['current_field'] == 'nationality':
            data['nationality'] = text
            keyboard = [
                [
                    InlineKeyboardButton("Higher", callback_data="Higher"),
                    InlineKeyboardButton("School", callback_data="School")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Select education level:", reply_markup=reply_markup)
            context.user_data['current_field'] = 'education'
            
        elif context.user_data['current_field'] == 'eye_color':
            data['eye_color'] = text
            await update.message.reply_text("Enter hair color:")
            context.user_data['current_field'] = 'hair_color'
            
        elif context.user_data['current_field'] == 'hair_color':
            data['hair_color'] = text
            await update.message.reply_text("Enter height (in cm):")
            context.user_data['current_field'] = 'height'
            
        elif context.user_data['current_field'] == 'height':
            try:
                height = int(text)
                if height <= 0:
                    raise ValueError
                data['height'] = height
                # Save data and finish
                await self.save_data(update, context, data)
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("Please enter a valid positive number for height (in cm):")
                return HUMAN_FLOW
                
        context.user_data['data'] = data
        return HUMAN_FLOW
    
    async def process_education(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process education selection for human flow"""
        query = update.callback_query
        await query.answer()
        
        # Edit message to show selection
        await query.message.edit_text(
            f"Select education level:\nSelected: {query.data}"
        )
        
        data = context.user_data.get('data', {})
        data['education'] = query.data
        context.user_data['data'] = data
        
        await query.message.reply_text("Enter eye color:")
        context.user_data['current_field'] = 'eye_color'
        return HUMAN_FLOW
    
    async def process_animal_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process animal classification flow"""
        if 'current_field' not in context.user_data:
            context.user_data['current_field'] = 'species'
            
        text = update.message.text
        data = context.user_data.get('data', {})
        
        if context.user_data['current_field'] == 'species':
            data['species'] = text
            keyboard = [
                [
                    InlineKeyboardButton("Yes", callback_data="Yes"),
                    InlineKeyboardButton("No", callback_data="No")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Is it a mammal?", reply_markup=reply_markup)
            context.user_data['current_field'] = 'mammal'
            
        elif context.user_data['current_field'] == 'color':
            data['color'] = text
            await update.message.reply_text("Enter weight (in kg):")
            context.user_data['current_field'] = 'weight'
            
        elif context.user_data['current_field'] == 'weight':
            try:
                weight = float(text)
                if weight <= 0:
                    raise ValueError
                data['weight'] = weight
                await update.message.reply_text("Enter age (in months):")
                context.user_data['current_field'] = 'age'
            except ValueError:
                await update.message.reply_text("Please enter a valid positive number for weight:")
                return ANIMAL_FLOW
                
        elif context.user_data['current_field'] == 'age':
            try:
                age = int(text)
                if age <= 0:
                    raise ValueError
                data['age'] = age
                # Save data and finish
                await self.save_data(update, context, data)
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("Please enter a valid positive number for age:")
                return ANIMAL_FLOW
                
        context.user_data['data'] = data
        return ANIMAL_FLOW
    
    async def process_animal_binary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process yes/no questions for animal flow"""
        query = update.callback_query
        await query.answer()
        
        data = context.user_data.get('data', {})
        current_field = context.user_data['current_field']
        
        if current_field == 'mammal':
            # Edit message to show selection
            await query.message.edit_text(
                f"Is it a mammal?\nSelected: {query.data}"
            )
            
            data['mammal'] = query.data
            keyboard = [
                [
                    InlineKeyboardButton("Yes", callback_data="Yes"),
                    InlineKeyboardButton("No", callback_data="No")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Is it a predator?", reply_markup=reply_markup)
            context.user_data['current_field'] = 'predator'
        elif current_field == 'predator':
            # Edit message to show selection
            await query.message.edit_text(
                f"Is it a predator?\nSelected: {query.data}"
            )
            
            data['predator'] = query.data
            await query.message.reply_text("Enter color:")
            context.user_data['current_field'] = 'color'
            
        context.user_data['data'] = data
        return ANIMAL_FLOW
    
    async def process_alien_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process alien classification flow"""
        if 'current_field' not in context.user_data:
            return ALIEN_FLOW
            
        text = update.message.text
        data = context.user_data.get('data', {})
        
        if context.user_data['current_field'] == 'race':
            if text.upper() not in ['X', 'Y', 'Z']:
                await update.message.reply_text("Please enter X, Y, or Z for race:")
                return ALIEN_FLOW
            data['race'] = text.upper()
            await update.message.reply_text("Enter skin color:")
            context.user_data['current_field'] = 'skin_color'
            
        elif context.user_data['current_field'] == 'skin_color':
            data['skin_color'] = text
            keyboard = [
                [
                    InlineKeyboardButton("Yes", callback_data="Yes"),
                    InlineKeyboardButton("No", callback_data="No")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text("Is it dangerous?", reply_markup=reply_markup)
            context.user_data['current_field'] = 'dangerous'
            
        elif context.user_data['current_field'] == 'weight':
            try:
                weight = float(text)
                if weight <= 0:
                    raise ValueError
                data['weight'] = weight
                # Save data and finish
                await self.save_data(update, context, data)
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("Please enter a valid positive number for weight:")
                return ALIEN_FLOW
                
        context.user_data['data'] = data
        return ALIEN_FLOW
    
    async def process_alien_binary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process yes/no questions for alien flow"""
        query = update.callback_query
        await query.answer()
        
        data = context.user_data.get('data', {})
        current_field = context.user_data.get('current_field')
        
        if current_field is None:  # First question - humanoid
            # Edit message to show selection
            await query.message.edit_text(
                f"Is it humanoid?\nSelected: {query.data}"
            )
            
            data['humanoid'] = query.data
            if query.data == 'Yes':
                await query.message.reply_text("Enter race (X/Y/Z):")
                context.user_data['current_field'] = 'race'
                context.user_data['data'] = data
                return ALIEN_FLOW
            else:
                # End conversation without saving data if not humanoid
                await query.message.reply_text("Non-humanoid alien classification cancelled.")
                context.user_data.clear()
                return ConversationHandler.END
                
        elif current_field == 'dangerous':
            # Edit message to show selection
            await query.message.edit_text(
                f"Is it dangerous?\nSelected: {query.data}"
            )
            
            data['dangerous'] = query.data
            keyboard = [
                [
                    InlineKeyboardButton("Yes", callback_data="Yes"),
                    InlineKeyboardButton("No", callback_data="No")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Has reason?", reply_markup=reply_markup)
            context.user_data['current_field'] = 'has_reason'
            
        elif current_field == 'has_reason':
            # Edit message to show selection
            await query.message.edit_text(
                f"Has reason?\nSelected: {query.data}"
            )
            
            data['has_reason'] = query.data
            await query.message.reply_text("Enter weight (in kg):")
            context.user_data['current_field'] = 'weight'
            
        context.user_data['data'] = data
        return ALIEN_FLOW

    async def save_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict):
        """Save the collected data to Google Sheets and post to Telegram group"""
        try:
            # Prepare sheet name
            sheet_name = f"{data['type']}s"
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Get the last row number and last used ID from sheet
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:B"
            ).execute()
            
            values = result.get('values', [])
            if len(values) > 1:  # If there are rows besides header
                try:
                    # Get last line number
                    line_numbers = [int(row[0]) for row in values[1:] if row[0].isdigit()]
                    line_number = max(line_numbers) + 1 if line_numbers else 1
                    
                    # Get last ID
                    ids = [int(row[1]) for row in values[1:] if len(row) > 1 and row[1].isdigit()]
                    last_id = max(ids) if ids else 9999
                except (ValueError, IndexError):
                    line_number = 1
                    last_id = 9999
            else:
                line_number = 1
                last_id = 9999
                
            # Generate new ID
            new_id = last_id + 1
            
            # Format data for Telegram post
            post_text = f"#{new_id}\n{today}\n"
            post_text += f"Specie: {data['type']}\n"
            
            for key, value in data.items():
                if key != 'type':
                    post_text += f"{key.replace('_', ' ').title()}: {value}\n"
            
            # Post to Telegram group
            group_id = os.getenv('TELEGRAM_GROUP_ID')
            if group_id:
                await context.bot.send_message(chat_id=group_id, text=post_text)
            
            # Prepare data for sheets
            row_data = [line_number, new_id]  # First two columns are line number and ID
            row_data.extend(list(data.values()))
            row_data.append(today)
            
            # Save to Google Sheets
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1:Z1",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row_data]}
            ).execute()
            
            # Clear user data
            context.user_data.clear()
            
            # Send confirmation to user
            message = "Classification completed and saved!"
            if update.message:
                await update.message.reply_text(message)
            else:
                await update.callback_query.message.reply_text(message)
                
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error in save_data: {e}")
            error_message = "An error occurred while saving the data. Please try again later."
            if update.message:
                await update.message.reply_text(error_message)
            else:
                await update.callback_query.message.reply_text(error_message)
            return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel and end the conversation."""
        context.user_data.clear()
        await update.message.reply_text("Classification cancelled.")
        return ConversationHandler.END
    
    def run(self):
        """Run the bot"""
        try:
            # Create application
            application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
            
            # Add conversation handler
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('classify', self.start_classification)],
                states={
                    BEING_TYPE: [CallbackQueryHandler(self.process_being_type)],
                    HUMAN_FLOW: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_human_data),
                        CallbackQueryHandler(self.process_education)
                    ],
                    ANIMAL_FLOW: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_animal_data),
                        CallbackQueryHandler(self.process_animal_binary)
                    ],
                    ALIEN_FLOW: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_alien_data),
                        CallbackQueryHandler(self.process_alien_binary)
                    ]
                },
                fallbacks=[
                    CommandHandler('cancel', self.cancel),
                    CommandHandler('classify', self.start_classification)
                ],
                per_message=False
            )
            
            application.add_handler(conv_handler)
            application.add_handler(CommandHandler("start", self.start))
            
            # Start the bot
            logger.info("Bot started successfully")
            application.run_polling()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise Exception(f"Failed to start bot: {e}")

if __name__ == '__main__':
    try:
        bot = BeingClassifierBot()
        bot.run()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise 
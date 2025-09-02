import os
import logging
from datetime import datetime
from typing import Optional
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, Application

from telegram_auth import (
    is_telegram_user_authenticated, 
    authenticate_telegram_user,
    get_remaining_block_time
)

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")

class TelegramBot:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
    
    async def start_command(self, update: Update, context) -> None:
        """Handle /start command."""
        if not update.effective_user:
            logger.warning("No user in /start command")
            return
            
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        logger.info(f"/start command from user {user_id}")
        
        if not update.message:
            return
            
        if is_telegram_user_authenticated(user_id):
            await update.message.reply_text(
                f"Hallo {user_name}! Du bist bereits eingeloggt.\n"
                "Schreib mir eine Nachricht und wir können mit dem Sprachtraining beginnen!"
            )
        else:
            await update.message.reply_text(
                f"Hallo {user_name}! Willkommen beim Sprachtrainer.\n"
                "Bitte gib das Passwort ein, um dich zu authentifizieren."
            )
    
    async def handle_message(self, update: Update, context) -> None:
        """Handle regular messages."""
        if not update.effective_user or not update.message or not update.message.text:
            logger.warning("Invalid message update")
            return
            
        user_id = update.effective_user.id
        message_text = update.message.text
        
        logger.info(f"Message from user {user_id}: {message_text}")
        
        # Check authentication
        if not is_telegram_user_authenticated(user_id):
            await self._handle_authentication(update, message_text)
        else:
            await self._handle_agent_chat(update, message_text)
    
    async def _handle_authentication(self, update: Update, message_text: str):
        """Handle password authentication."""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        
        # Check rate limiting
        remaining_time = get_remaining_block_time(user_id)
        if remaining_time and remaining_time > 0:
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            await update.message.reply_text(
                f"Zu viele fehlgeschlagene Versuche. "
                f"Bitte warte noch {minutes}:{seconds:02d} Minuten."
            )
            return
        
        # Try to authenticate
        if authenticate_telegram_user(user_id, message_text, update.effective_user):
            user_name = update.effective_user.first_name or "User"
            await update.message.reply_text(
                f"Authentifizierung erfolgreich! Willkommen {user_name}!"
            )
        else:
            await update.message.reply_text(
                "Falsches Passwort. Bitte versuche es erneut."
            )
    
    async def _handle_agent_chat(self, update: Update, message_text: str):
        """Handle chat with the language trainer agent."""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        
        try:
            # Create session ID
            today = datetime.now().strftime('%Y%m%d')
            session_id = f"telegram:{user_id}:{today}"
            
            # Call agent API
            response = await self._call_agent_api(session_id, message_text)
            
            if response:
                # Format response for Telegram
                formatted_response = self._format_response_for_telegram(response)
                await update.message.reply_text(formatted_response)
            else:
                await update.message.reply_text(
                    "Entschuldigung, ich kann gerade nicht antworten. Versuche es bitte später nochmal."
                )
                
        except Exception as e:
            logger.error(f"Error handling agent chat for user {user_id}: {e}")
            await update.message.reply_text(
                "Es ist ein Fehler aufgetreten. Bitte versuche es erneut."
            )
    
    async def _call_agent_api(self, session_id: str, message: str) -> Optional[str]:
        """Call the language trainer agent directly."""
        try:
            from trainer_agent_with_tools import trainer
            
            logger.info(f"Calling agent directly with session {session_id}")
            
            # Call the agent directly using Agno framework
            # Use run method with session_id parameter
            response = trainer.run(message, session_id=session_id)
            
            # Extract text from Agno RunResponse
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'messages') and response.messages:
                # Get last message content
                last_message = response.messages[-1]
                if hasattr(last_message, 'content'):
                    content = last_message.content
                    return str(content) if content is not None else None
            
            # Fallback to string representation
            return str(response)
                    
        except Exception as e:
            logger.error(f"Error calling agent directly: {e}")
            return None
    
    def _format_response_for_telegram(self, response: str) -> str:
        """Format HTML response for Telegram plain text."""
        if not response:
            return "Keine Antwort erhalten."
        
        # Convert HTML breaks to newlines
        formatted = response.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        
        # Remove other HTML tags (simple approach)
        import re
        formatted = re.sub(r'<[^>]+>', '', formatted)
        
        # Clean up extra whitespace
        formatted = '\n'.join(line.strip() for line in formatted.split('\n') if line.strip())
        
        return formatted if formatted else "Keine Antwort erhalten."
    
    async def setup_bot_commands(self, application: Application):
        """Setup bot commands."""
        commands = [
            BotCommand("start", "Bot starten und einloggen"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands configured")

def create_telegram_application():
    """Create and configure the Telegram application."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
    
    # Create bot instance
    bot = TelegramBot()
    
    # Build application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Webhook security is handled in the FastAPI endpoint via header validation
    if TELEGRAM_WEBHOOK_SECRET:
        logger.info("Webhook secret configured - validation handled in FastAPI endpoint")
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bot.handle_message))
    
    # Setup commands
    async def post_init(app):
        await bot.setup_bot_commands(app)
    
    application.post_init = post_init
    
    return application

if __name__ == "__main__":
    # For testing - run bot in polling mode
    logging.basicConfig(level=logging.INFO)
    
    app = create_telegram_application()
    print("Starting Telegram bot in polling mode...")
    app.run_polling()
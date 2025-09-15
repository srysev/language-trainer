from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.playground import Playground
from agno.tools import tool
import random
import os
import logging
import asyncio
from agno.memory.v2.schema import UserMemory
from agno.storage.sqlite import SqliteStorage
from agno.storage.mongodb import MongoDbStorage
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.db.mongodb import MongoMemoryDb
from agno.memory.v2.memory import Memory
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import certifi

# --- Configuration ---
MONGO_URL = os.getenv('MONGO_URL')
agent_storage = "tmp/agents.db"

# --- Difficulty System Constants ---
DIFFICULTY_MEMORY_ID = "kyrill_difficulty_level"
USER_ID = "kyrill"
REVIEW_TRIGGER_INTERVAL = 5  # Trigger review every N interactions

# --- Difficulty Instructions Dictionary ---
DIFFICULTY_INSTRUCTIONS = {
    "Kyrills aktuelle Schwierigkeitsstufe ist 1": """
SCHWIERIGKEIT STUFE 1 - EINDEUTIGE WAHL:
- Sätze: EXAKT 3-5 Wörter, nie mehr
- Lücke: GENAU eine Lücke mit ___
- Optionen: EXAKT zwei Optionen mit /
- Richtige Option: muss logisch und grammatisch korrekt sein
- Falsche Option: völlig andere Wortart oder Kategorie (z.B. Essen vs. Fahrzeug)
- Verwende nur bekannte Grundwörter (Wasser, Brot, Auto, Haus)
- Beispiel: "Ich trinke ___." → "Optionen: Wasser / Auto"
""",
    
    "Kyrills aktuelle Schwierigkeitsstufe ist 2": """
SCHWIERIGKEIT STUFE 2 - ÄHNLICHE ABLENKER:
- Sätze: EXAKT 3-5 Wörter, nie mehr  
- Lücke: GENAU eine Lücke mit ___
- Optionen: EXAKT zwei Optionen mit /
- Beide Optionen: gleiche Wortart, gleiche Kategorie
- Nur eine Option: semantisch sinnvoll im Kontext
- Beispiel: "Ich esse ___." → "Optionen: Brot / Saft" (beide Lebensmittel, aber nur Brot passt zu "essen")
""",
    
    "Kyrills aktuelle Schwierigkeitsstufe ist 3": """
SCHWIERIGKEIT STUFE 3 - LÄNGERE SÄTZE:
- Sätze: EXAKT 6-8 Wörter mit Zeitangaben/Adjektiven
- Lücke: GENAU eine Lücke mit ___
- Optionen: EXAKT zwei Optionen mit /
- Logik wie Stufe 1: eine richtig, eine völlig falsch
- Beispiel: "Heute Morgen habe ich meinen Kaffee ___." → "Optionen: getrunken / gefahren"
""",
    
    "Kyrills aktuelle Schwierigkeitsstufe ist 4": """
SCHWIERIGKEIT STUFE 4 - DREI OPTIONEN:
- Sätze: EXAKT 4-6 Wörter
- Lücke: GENAU eine Lücke mit ___  
- Optionen: EXAKT drei Optionen mit / zwischen allen
- Eine Option: richtig und passend
- Zwei Optionen: aus völlig anderen Bereichen/Kategorien
- Beispiel: "Am Computer arbeite ich mit der ___." → "Optionen: Maus / Schere / Gabel"
""",
    
    "Kyrills aktuelle Schwierigkeitsstufe ist 5": """
SCHWIERIGKEIT STUFE 5 - GRAMMATIK-FOKUS:
- Sätze: EXAKT 5-7 Wörter
- Lücke: GENAU eine Lücke mit ___
- Optionen: EXAKT 2-3 grammatische Formen desselben Wortes
- Nur eine Form: grammatisch korrekt im Satzkontext  
- Fokus: Perfekt vs. Infinitiv vs. Präsens
- Beispiel: "Gestern habe ich einen Brief ___." → "Optionen: geschrieben / schreiben / schreibt"
""",
    
    "Kyrills aktuelle Schwierigkeitsstufe ist 6": """
SCHWIERIGKEIT STUFE 6 - FREIE EINGABE:
- Sätze: EXAKT 4-6 Wörter
- Lücke: GENAU eine Lücke mit ___
- KEINE Optionen anbieten
- Erwarte Kyrills freie Eingabe
- Akzeptiere mehrere korrekte Antworten
- Beispiel: "Ich arbeite am ___." (Akzeptiere: Computer, Schreibtisch, Laptop)
"""
}

# --- Logging Setup ---
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- MongoDB Client Singleton ---
_mongodb_client = None

def get_mongodb_client():
    """Get singleton MongoDB client instance."""
    global _mongodb_client
    if _mongodb_client is None:
        _mongodb_client = MongoClient(
            MONGO_URL,
            server_api=ServerApi("1"),
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=30000,
        )
    return _mongodb_client

# --- Storage and Memory initialization ---
def get_storage_and_memory():
    """Initialize both storage and memory with shared configuration."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        logger.info("Initializing MongoDB storage and memory for production...")
        try:
            client = get_mongodb_client()  # Nur einmal initialisiert
            
            storage = MongoDbStorage(
                client=client,
                db_name="language_trainer",
                collection_name="language_trainer_storage"
            )
            
            memory_db = MongoMemoryDb(
                client=client,  # Gleicher Client!
                db_name="language_trainer",
                collection_name="language_trainer_memory"
            )
            memory = Memory(db=memory_db)  # type: ignore
            
            logger.info("MongoDB storage and memory initialized")
            return storage, memory
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB storage/memory: {e}")
            logger.info("Falling back to SQLite storage and memory")
    
    # SQLite Fallback
    logger.info("Using SQLite storage and memory")
    storage = SqliteStorage(table_name="trainer", db_file=agent_storage)
    memory_db = SqliteMemoryDb(db_file="tmp/trainer_memory.db")
    memory = Memory(db=memory_db)
    
    return storage, memory

# --- Memory Management Functions ---
def get_memory_by_id(memory_instance, user_id, memory_id):
    """
    Workaround for defective get_user_memory() in Agno Framework.
    Uses get_user_memories() and filters manually.
    
    Args:
        memory_instance: Memory instance (agent.memory or global memory)
        user_id: User ID to search for
        memory_id: Memory ID to find
        
    Returns:
        UserMemory object or None if not found
    """
    try:
        all_memories = memory_instance.get_user_memories(user_id=user_id)
        return next((m for m in all_memories if m.memory_id == memory_id), None)
    except Exception as e:
        logger.error(f"Error in get_memory_by_id: {e}")
        return None

def ensure_difficulty_memory(agent):
    """
    Ensure difficulty memory exists and return current difficulty instruction text.
    Creates initial Level 1 if no memory exists.
    
    Returns:
        str: Memory text that serves as key for DIFFICULTY_INSTRUCTIONS
    """
    # Use workaround function instead of defective get_user_memory
    memory = get_memory_by_id(agent.memory, USER_ID, DIFFICULTY_MEMORY_ID)
    if memory and memory.memory in DIFFICULTY_INSTRUCTIONS:
        logger.info(f"Retrieved difficulty memory: {memory.memory}")
        return memory.memory
    else:
        logger.info("No existing difficulty memory found or invalid content")
    
    # Create initial Level 1 memory
    initial_difficulty_text = "Kyrills aktuelle Schwierigkeitsstufe ist 1"
    initial_memory = UserMemory(
        memory=initial_difficulty_text,
        topics=["schwierigkeitsstufe"],
        memory_id=DIFFICULTY_MEMORY_ID
    )
    
    try:
        agent.memory.add_user_memory(initial_memory, user_id=USER_ID)
        logger.info(f"Created initial difficulty memory: {initial_difficulty_text}")
    except Exception as e:
        logger.error(f"Failed to create initial difficulty memory: {e}")
    
    return initial_difficulty_text

def update_difficulty_memory(agent, new_difficulty_text):
    """
    Update difficulty memory with new level.
    
    Args:
        agent: The trainer agent
        new_difficulty_text: New difficulty text (must be key in DIFFICULTY_INSTRUCTIONS)
    """
    if new_difficulty_text not in DIFFICULTY_INSTRUCTIONS:
        logger.error(f"Invalid difficulty text: {new_difficulty_text}")
        return
    
    new_memory = UserMemory(
        memory=new_difficulty_text,
        topics=["schwierigkeitsstufe"],
        memory_id=DIFFICULTY_MEMORY_ID
    )
    
    try:
        # Use add_user_memory as UPSERT (creates or updates)
        agent.memory.add_user_memory(new_memory, user_id=USER_ID)
        logger.info(f"Updated difficulty memory to: {new_difficulty_text}")
        
        # Update agent instructions immediately
        set_agent_instructions_for_difficulty(agent, new_difficulty_text)
        
    except Exception as e:
        logger.error(f"Failed to update difficulty memory: {e}")

def set_agent_instructions_for_difficulty(agent, difficulty_text):
    """
    Set agent instructions based on current difficulty level.
    
    Args:
        agent: The trainer agent
        difficulty_text: Current difficulty text (key in DIFFICULTY_INSTRUCTIONS)
    """
    if difficulty_text not in DIFFICULTY_INSTRUCTIONS:
        logger.error(f"Unknown difficulty text: {difficulty_text}")
        difficulty_text = "Kyrills aktuelle Schwierigkeitsstufe ist 1"  # Fallback
    
    # Get the difficulty-specific instructions
    difficulty_instructions = DIFFICULTY_INSTRUCTIONS[difficulty_text]
    
    # Build the instructions array - SCHLANK UND FOKUSSIERT
    agent.instructions = [
        f"Du bist Kyrills Sprachtrainer. {difficulty_text}",
        
        difficulty_instructions,
        
        """DIALOGFLUSS:
1) Nutze generate_task Tool (Parameter abhängig von aktueller Stufe)
2) Gib String direkt aus
3) Bei richtiger Antwort: "Richtig. Sehr gut."
4) Bei falscher Antwort: "Das passt nicht. Richtig ist: <Wort>."
5) Sofort nächste Aufgabe
6) Bei "Stop"/"Pause": freundlich verabschieden

STIL: Deutsch, kurz (max 8 Wörter), warm, keine Erklärungen.
WÖRTER: Nur bekannte Grundwörter (Haushalt/Arbeit/Gefühle).
ERSTE NACHRICHT: Kurze Begrüßung + Beispiel + erste Aufgabe."""
    ]
    
    logger.info(f"Set agent instructions for difficulty: {difficulty_text}")

@tool(
    name="generate_task",
    description="""Erstellt formatierte Sprachtraining-Aufgaben für alle 6 Schwierigkeitsstufen.

FUNKTIONSWEISE:
- Nimmt einen Satz mit ___ Lücke und Antwortoptionen
- Gibt HTML-formatierten String zurück: 'Satz ___<br>Optionen: A / B' oder 'Satz ___<br>Schreib deine Antwort:'
- Randomisiert automatisch die Reihenfolge der Optionen

MODI (automatische Erkennung):
• Level 1,2,3,5: 2 Optionen → generate_task('Ich trinke ___', 'Wasser', 'Auto', '')
• Level 4: 3 Optionen → generate_task('Computer ___', 'Maus', 'Schere', 'Gabel') 
• Level 6: Freie Eingabe → generate_task('Ich arbeite am ___', '', '', '') - ALLE OPTIONEN LEER!

ERGEBNIS-BEISPIELE:
- 2 Optionen: 'Ich trinke ___<br>Optionen: Auto / Wasser' (randomisierte Reihenfolge)
- 3 Optionen: 'Am Computer arbeite ich mit der ___<br>Optionen: Gabel / Maus / Schere' (randomisiert)
- Freie Eingabe: 'Ich arbeite am ___<br>Schreib deine Antwort:' (keine Optionen)"""
)
def generate_task(sentence_with_blank: str, correct_option: str = "", wrong_option1: str = "", wrong_option2: str = "") -> str:
    """
    Intelligentes Tool für alle Schwierigkeitsstufen - wählt automatisch richtiges Format.
    
    Args:
        sentence_with_blank: Satz mit ___ Platzhalter (immer erforderlich)
        correct_option: Richtige Antwort (leer bei Level 6)
        wrong_option1: Erste falsche Option (leer bei Level 6)
        wrong_option2: Zweite falsche Option (nur bei Level 4 gesetzt, leer bei anderen)
        
    Returns:
        Formatierter HTML-String mit Aufgabe und Optionen oder Eingabeaufforderung
    """
    # Automatische Modus-Erkennung basierend auf Parametern
    if not correct_option.strip() and not wrong_option1.strip() and not wrong_option2.strip():
        # Level 6: Alle Parameter leer = Freie Eingabe
        logger.debug("Level 6: Free input mode - all options empty")
        return f"{sentence_with_blank}<br>Schreib deine Antwort:"
    
    elif wrong_option2.strip():
        # Level 4: Drei Optionen wenn wrong_option2 gegeben
        if not correct_option.strip() or not wrong_option1.strip():
            logger.error("Three options mode requires correct_option, wrong_option1 AND wrong_option2")
            return f"{sentence_with_blank}<br>Fehler: Unvollständige Optionen"
        
        # Randomisiere Reihenfolge der drei Optionen
        options = [correct_option, wrong_option1, wrong_option2]
        random.shuffle(options)
        logger.debug(f"Level 4: Three options mode: {options}")
        return f"{sentence_with_blank}<br>Optionen: {options[0]} / {options[1]} / {options[2]}"
    
    elif correct_option.strip() and wrong_option1.strip():
        # Level 1,2,3,5: Zwei Optionen (Standard)
        # Randomisiere Reihenfolge der zwei Optionen
        if random.choice([True, False]):
            option_line = f"Optionen: {correct_option} / {wrong_option1}"
        else:
            option_line = f"Optionen: {wrong_option1} / {correct_option}"
        
        logger.debug(f"Level 1-3,5: Two options mode: {option_line}")
        return f"{sentence_with_blank}<br>{option_line}"
    
    else:
        # Fallback: Unvollständige Parameter
        logger.error(f"Invalid parameters: correct='{correct_option}', wrong1='{wrong_option1}', wrong2='{wrong_option2}'")
        return f"{sentence_with_blank}<br>Fehler: Unvollständige Parameter"

# Note: All redundant wrapper functions removed - only generate_task needed!

# --- Clean TrainerAgent with Built-in Review System ---
class TrainerAgent(Agent):
    """
    Enhanced Agent with automatic difficulty review system.
    Simple inheritance approach - much cleaner than wrapper functions.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction_count = 0
    
    def run(self, message, **kwargs):
        """Override run method with review system"""
        # Execute original run
        response = super().run(message, **kwargs)
        
        # Update interaction count and trigger review if needed
        self._handle_interaction()
        
        return response
    
    async def arun(self, message, **kwargs):
        """Override arun method with review system"""
        # Execute original arun
        response = await super().arun(message, **kwargs)
        
        # Update interaction count and trigger review if needed
        await self._handle_interaction_async()
        
        return response
    
    def _handle_interaction(self):
        """Handle interaction counting and sync review trigger"""
        self.interaction_count += 1
        logger.debug(f"Interaction count: {self.interaction_count}")
        
        if self.interaction_count % REVIEW_TRIGGER_INTERVAL == 0:
            logger.info(f"Triggering review after {self.interaction_count} interactions")
            try:
                asyncio.create_task(self._trigger_review())
            except RuntimeError:
                logger.info("No event loop for async review in sync context")
    
    async def _handle_interaction_async(self):
        """Handle interaction counting and async review trigger"""
        self.interaction_count += 1
        logger.debug(f"Async interaction count: {self.interaction_count}")
        
        if self.interaction_count % REVIEW_TRIGGER_INTERVAL == 0:
            logger.info(f"Triggering async review after {self.interaction_count} interactions")
            asyncio.create_task(self._trigger_review())
    
    async def _trigger_review(self):
        """Simple review trigger - no complex agent_instance confusion"""
        try:
            from complexity_review_agent import analyze_conversation_difficulty_async
            
            # Get current difficulty using workaround function
            current_memory = get_memory_by_id(self.memory, USER_ID, DIFFICULTY_MEMORY_ID)
            current_difficulty_text = current_memory.memory if current_memory else "Kyrills aktuelle Schwierigkeitsstufe ist 1"
            logger.info(f"Review: Using difficulty from memory: {current_difficulty_text}")
            
            # Get conversation history from THIS agent
            messages = self.get_messages_for_session() if hasattr(self, 'get_messages_for_session') else []
            conversation_history = "\n".join([f"User: {msg.content}" if hasattr(msg, 'content') else str(msg) for msg in messages[-20:]])
            
            if not conversation_history.strip():
                logger.info("No conversation history for review")
                return
            
            # Run review analysis
            logger.info("Starting background complexity review")
            new_difficulty = await analyze_conversation_difficulty_async(conversation_history, current_difficulty_text)
            
            if new_difficulty and new_difficulty != current_difficulty_text:
                logger.info(f"Review recommends difficulty change: {current_difficulty_text} -> {new_difficulty}")
                update_difficulty_memory(self, new_difficulty)  # Use self - much cleaner!
            else:
                logger.info(f"Review recommends keeping current difficulty: {current_difficulty_text}")
                
        except Exception as e:
            logger.error(f"Error in background review: {e}")

# Initialize storage and memory
storage, memory = get_storage_and_memory()

# Create trainer agent using our clean TrainerAgent class
trainer = TrainerAgent(
    name="Sprachtrainer",
    model=OpenAIChat(id="gpt-4.1"),
    description="Du bist ein Sprachtrainer für Kyrill.",
    instructions=["Placeholder - wird durch ensure_difficulty_memory() gesetzt"],  # Temporary placeholder
    storage=storage,
    memory=memory,
    enable_agentic_memory=True,
    tools=[generate_task],
    add_history_to_messages=True,
    show_tool_calls=False,
    markdown=False,
)

# Initialize difficulty memory and set appropriate instructions
current_difficulty = ensure_difficulty_memory(trainer)
set_agent_instructions_for_difficulty(trainer, current_difficulty)

playground = Playground(agents=[trainer])
app = playground.get_app()

if __name__ == "__main__":
    # Passe den Modulpfad an den Dateinamen an:
    playground.serve("trainer_agent_with_tools:app", reload=True)

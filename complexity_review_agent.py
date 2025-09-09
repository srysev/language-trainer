from agno.agent import Agent
from agno.models.openai import OpenAIChat
import logging
from typing import Optional, Literal
from pydantic import BaseModel, Field

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# --- Structured Output Model ---
class DifficultyRecommendation(BaseModel):
    """Structured output for difficulty level recommendations."""
    recommendation: str = Field(
        ...,
        description="Exact difficulty level text",
        pattern="^Kyrills aktuelle Schwierigkeitsstufe ist [1-6]$"
    )
    confidence: Literal["hoch", "mittel", "niedrig"] = Field(
        ...,
        description="Confidence level"
    )
    reasoning: str = Field(
        ...,
        description="Brief reasoning for the recommendation (max 2 sentences)"
    )

# Create the review agent with structured output
review_agent = Agent(
    name="Complexity Review Agent",
    model=OpenAIChat(id="o4-mini"),
    response_model=DifficultyRecommendation,
    description="Analysiert Kyrills Lernfortschritt und empfiehlt Schwierigkeitsstufen-Anpassungen.",
    instructions="""Du bist ein Lernfortschritts-Analyst für Kyrills Sprachtraining.

DEINE AUFGABE:
Analysiere die Conversation History und empfehle eine passende Schwierigkeitsstufe von 1-6.

SCHWIERIGKEITSSTUFEN-ÜBERSICHT:
- Stufe 1: Eindeutige Wahl (2 Optionen, völlig unterschiedlich) - für Anfänger
- Stufe 2: Ähnliche Ablenker (2 Optionen, gleiche Kategorie) - leicht fortgeschritten  
- Stufe 3: Längere Sätze (2 Optionen, mehr Kontext) - mehr Herausforderung
- Stufe 4: Drei Optionen (3 Optionen, verschiedene Kategorien) - deutlich schwerer
- Stufe 5: Grammatik-Fokus (2-3 Optionen, gleiche Grundform) - für Grammatik
- Stufe 6: Freie Eingabe (keine Optionen) - höchste Stufe

BEWERTUNGSKRITERIEN:
1. Erfolgsrate der letzten 5-10 Aufgaben
2. Antwortgeschwindigkeit/Zögern
3. Fehlerarten (zufällige Fehler vs. systematische Probleme)
4. Engagement-Level (lange vs. kurze Antworten, Motivation)

ENTSCHEIDUNGSLOGIK:
- 90%+ korrekt, schnelle Antworten → Stufe erhöhen
- 70-90% korrekt → Stufe beibehalten  
- 50-70% korrekt → eine Stufe senken
- <50% korrekt → zwei Stufen senken
- Nie unter Stufe 1 oder über Stufe 6""",
    storage=None,  # No storage needed for review agent
    memory=None,   # No memory needed for review agent
    add_history_to_messages=False,
    show_tool_calls=False,
    markdown=False,
)

def analyze_conversation_difficulty(conversation_history: str, current_difficulty: str) -> Optional[str]:
    """
    Analyze conversation and recommend difficulty level.
    
    Args:
        conversation_history: Full conversation history as string
        current_difficulty: Current difficulty level text
        
    Returns:
        str: Recommended difficulty level text, or None if analysis fails
    """
    try:
        # Prepare analysis prompt
        analysis_prompt = f"""Analysiere diese Conversation History von Kyrill's Sprachtraining:

AKTUELLE STUFE: {current_difficulty}

CONVERSATION HISTORY:
{conversation_history}

Analysiere Kyrills Leistung und empfehle die passende Schwierigkeitsstufe."""
        
        # Run analysis
        response = review_agent.run(analysis_prompt)
        
        # Extract recommendation from structured output
        # With response_model, Agno should return the structured data directly
        if hasattr(response, 'content') and isinstance(response.content, DifficultyRecommendation):
            result = response.content
            logger.info(f"Review agent recommendation: {result.recommendation} (confidence: {result.confidence})")
            logger.debug(f"Reasoning: {result.reasoning}")
            return result.recommendation
        elif isinstance(response, DifficultyRecommendation):
            logger.info(f"Review agent recommendation: {response.recommendation} (confidence: {response.confidence})")
            logger.debug(f"Reasoning: {response.reasoning}")
            return response.recommendation
        elif hasattr(response, 'content'):
            # Fallback: try to access content directly
            logger.info(f"Review agent recommendation: {response.content}")
            return str(response.content)
        else:
            logger.warning(f"Unexpected response format: {type(response)} - {response}")
            return None
            
    except Exception as e:
        logger.error(f"Error in conversation analysis: {e}")
        return None

async def analyze_conversation_difficulty_async(conversation_history: str, current_difficulty: str) -> Optional[str]:
    """
    Async version of conversation analysis.
    
    Args:
        conversation_history: Full conversation history as string
        current_difficulty: Current difficulty level text
        
    Returns:
        str: Recommended difficulty level text, or None if analysis fails
    """
    try:
        # Prepare analysis prompt
        analysis_prompt = f"""Analysiere diese Conversation History von Kyrill's Sprachtraining:

AKTUELLE STUFE: {current_difficulty}

CONVERSATION HISTORY:
{conversation_history}

Analysiere Kyrills Leistung und empfehle die passende Schwierigkeitsstufe."""
        
        # Run analysis asynchronously
        response = await review_agent.arun(analysis_prompt)
        
        # Extract recommendation from structured output
        # With response_model, Agno should return the structured data directly
        if hasattr(response, 'content') and isinstance(response.content, DifficultyRecommendation):
            result = response.content
            logger.info(f"Async review agent recommendation: {result.recommendation} (confidence: {result.confidence})")
            logger.debug(f"Async reasoning: {result.reasoning}")
            return result.recommendation
        elif isinstance(response, DifficultyRecommendation):
            logger.info(f"Async review agent recommendation: {response.recommendation} (confidence: {response.confidence})")
            logger.debug(f"Async reasoning: {response.reasoning}")
            return response.recommendation
        elif hasattr(response, 'content'):
            # Fallback: try to access content directly
            logger.info(f"Async review agent recommendation: {response.content}")
            return str(response.content)
        else:
            logger.warning(f"Unexpected async response format: {type(response)} - {response}")
            return None
            
    except Exception as e:
        logger.error(f"Error in async conversation analysis: {e}")
        return None
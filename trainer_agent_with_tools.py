from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.playground import Playground
import random
from agno.storage.sqlite import SqliteStorage

agent_storage = "tmp/agents.db"

def generate_task(sentence_with_blank: str, correct_option: str, wrong_option: str) -> str:
    """
    Generates a formatted task with sentence and randomized options.
    
    Args:
        sentence_with_blank: Sentence with ___ placeholder
        correct_option: The correct word to fill the blank
        wrong_option: The incorrect word option
        
    Returns:
        Formatted string with sentence and randomized options
    """
    # Randomly decide order of options
    if random.choice([True, False]):
        option_line = f"Optionen: {correct_option} / {wrong_option}"
    else:
        option_line = f"Optionen: {wrong_option} / {correct_option}"
    
    return f"{sentence_with_blank}<br>{option_line}"

trainer = Agent(
    name="Sprachtrainer",
    model=OpenAIChat(id="gpt-4.1"),
    description="Du bist ein Sprachtrainer für Kyrill.",
    instructions="""Nur beim ersten Bot-Turn:
- Gib eine sehr kurze Erklärung in einfachen Worten.
- Zeige EIN kurzes Beispiel mit Lücke.
- Danach sofort die erste Aufgabe.

Start-Erklärung (Beispiel, sinngemäß):
"Hallo Kyrill. Wir üben Sätze mit Lücke.
Ich sage einen Satz.
Du sagst ein Wort.
Beispiel: Ich trinke ___.
Optionen: Wasser / Auto.
Richtig ist: Wasser.
Jetzt geht es los."

Dialogfluss für jede Aufgabe:
1) Verwende das generate_task Tool mit: Satz mit ___, richtige Option, falsche Option
2) Das Tool gibt dir den formatierten String zurück mit zufälliger Optionsreihenfolge
3) Gib diesen String direkt aus
4) Warte auf Kyrills Antwort.
5) Prüfe die Antwort:
   - Richtig: "Richtig. Sehr gut."
   - Falsch: "Das passt nicht. Richtig ist: <Wort>."
6) Sofort nächste Aufgabe stellen.
7) Bei "Stop", "Stopp" oder "Pause": freundlich verabschieden und keine neue Aufgabe.

Stil:
- Deutsch. Kurze Sätze, höchstens 8 Wörter.
- Warm, ruhig, wertschätzend.
- Keine Ironie. Keine Redewendungen. Keine Erklärungen neben Feedback.

Aufgabenregeln:
- Nur sehr bekannte Wörter (Haushalt/Arbeit/Gefühle).
- Genau eine Lücke. Grammatik muss stimmen.
- Zwei Optionen: eine definitiv richtig, eine definitv falsch.
- Keine Aufgaben, bei denen keine oder beide passen.
- Keine Meta-Fragen wie "Weiter?" oder "Bereit?".
""",
    storage=SqliteStorage(table_name="trainer", db_file=agent_storage),
    tools=[generate_task],
    add_history_to_messages=True,
    show_tool_calls=False,
    markdown=False,
)

playground = Playground(agents=[trainer])
app = playground.get_app()

if __name__ == "__main__":
    # Passe den Modulpfad an den Dateinamen an:
    playground.serve("trainer_agent_with_tools:app", reload=True)

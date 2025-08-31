# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Activate virtual environment (required for all operations)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Run main FastAPI application with UI
python app.py

# Run standalone trainer agent (development mode)
python trainer_agent_with_tools.py

# Alternative standalone mode
python trainer_agent.py

# Run with Docker
docker build -t sprachtrainer .
docker run -p 8080:8080 -e AUTH_PASSWORD=your_password sprachtrainer
```

The main application runs on port 8080 and serves both API endpoints and the web UI.

## Architecture Overview

### Core Components

**FastAPI Application (`app.py`)**
- Main entry point using Agno framework
- Combines agent backend with static file serving
- Routes: `/` (UI), `/static/*` (assets), `/v1/*` (agent API), `/login` (auth)
- Agent accessible via `?agent_id=sprachtrainer`
- Password authentication via middleware (optional, set `AUTH_PASSWORD` env var)

**AI Agent System**
- Uses Agno framework with OpenAI GPT models
- `trainer_agent.py`: Basic agent without tools
- `trainer_agent_with_tools.py`: Enhanced agent with task generation tools
- SQLite storage for conversation history in `tmp/agents.db`

**Frontend (`static/`)**
- Simple HTML/CSS/JS chat interface
- Real-time communication with agent via API
- German language interface ("Nachricht eingeben...")

### Data Flow
1. User interacts with web UI
2. Messages sent to FastAPI agent endpoints
3. Agent processes via OpenAI model with custom instructions
4. Responses formatted with gap-fill exercises and options
5. Conversation history stored in SQLite

### Agent Configuration
- Target user: "Kyrill" (German language learner)
- Exercise format: Single gap-fill with two options
- Instructions emphasize short sentences, familiar words
- Randomized option ordering via `generate_task` tool
- History tracking (5 previous responses)

### Database Structure
- Agent storage: `tmp/agents.db` (conversation history)
- Additional DBs: `tmp/language_trainer.db`, `tmp/satztrainer.db` (likely legacy)

## Development Notes

### Agent Customization
- Agent instructions are embedded in Python files
- Model can be changed between `gpt-4.1-mini` and `gpt-4.1`
- Tool system allows extending agent capabilities
- Storage configuration uses SQLite with configurable table names

### File Organization
- `app.py`: Production FastAPI server
- `trainer_agent*.py`: Development/standalone modes
- `static/`: Frontend assets (HTML/CSS/JS)
- `tmp/`: Database files (gitignored)
- `venv/`: Python virtual environment
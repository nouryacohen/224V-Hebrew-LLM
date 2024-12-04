from typing import List, Dict, Optional, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from pathlib import Path
from datetime import datetime
from ..call_gpt_api import call_gpt_api
from ..data.data_processing import get_data_list

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WordHistory(BaseModel):
    observations: List[Dict[str, str]] = []  # List of {timestamp, comment} dicts
    last_used: Optional[str] = None

class UserProgress(BaseModel):
    word_history: Dict[str, WordHistory] = {}  # word: WordHistory
    role_play: Optional[str] = None
    current_position: int = 0
    conversation_history: List[str] = []

class ConversationInput(BaseModel):
    username: str
    user_message: str
    role_play: Optional[str] = None

class ConversationResponse(BaseModel):
    response: str
    word_history: Dict[str, WordHistory]
    next_words_to_learn: List[str]
    current_position: int

class QueryInput(BaseModel):
    query: str
    username: str

DATA_DIR = Path("user_data")
DATA_DIR.mkdir(exist_ok=True)
FREQUENCY_LIST = get_data_list()

def add_observation(history: WordHistory, comment: str) -> WordHistory:
    """Add a new observation to word history"""
    history.observations.append({
        "timestamp": datetime.now().isoformat(),
        "comment": comment
    })
    history.last_used = datetime.now().isoformat()
    return history

class UserStorage:
    @staticmethod
    def get_user_file_path(username: str) -> Path:
        return DATA_DIR / f"{username}.json"

    @staticmethod
    def save_user_data(username: str, progress: UserProgress):
        file_path = UserStorage.get_user_file_path(username)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(progress.dict(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_user_data(username: str) -> UserProgress:
        file_path = UserStorage.get_user_file_path(username)
        if not file_path.exists():
            return UserProgress()
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return UserProgress(**data)

class PromptTemplate:
    @staticmethod
    def create_system_prompt() -> str:
        return """You are a language learning buddy helping users learn Hebrew through natural conversation. You will:
        1. Match the user's level based on their word history
        If a user is giving you short responses, respond with less complicated words.
        2. Use well-understood words as a foundation
        3. Match the roleplay context if provided
        4. Keep responses concise and conversational (1-2 sentences)
        5. Never directly explain word meanings - let users learn through context
        6. Never use English translations in parentheses
        7. Ensure natural conversation flow
        8. Talk as a friend, not a tutor
        9. MOST importantly! Match the users level based off of their corpus and the questions they have asked, reinforcing words they just asked about and matching their level. 
        10. If a user is responding shortly that means their level is low, if the user history shows that they just asked about a basic word, lower the level. Use the history to match their level as a roleplay assistant.
        11. THE ENTIRE GOAL IS TO TEACH THEM THE 1000 MOST COMMON WORDS!! If they are asking about a word re-use them, do not ask obscure words, introduce words slowly!!"""

    @staticmethod
    def create_conversation_prompt(
        role_play: Optional[str],
        user_message: str,
        word_history: Dict[str, WordHistory],
        next_words: List[str],
        conversation_history: List[str]
    ) -> str:
        role_context = f"\nYou are {role_play} having a conversation. Maintain character but keep language appropriate to user's level." if role_play else ""
        
        history_str = "\n".join(conversation_history[-6:]) if conversation_history else "No previous conversation"

        word_knowledge = []
        for word, history in word_history.items():
            if history.observations:
                observations = [f"- {obs['timestamp']}: {obs['comment']}" 
                              for obs in sorted(history.observations, 
                                              key=lambda x: x['timestamp'])]
                word_summary = f"{word}:\n" + "\n".join(observations)
                word_knowledge.append(word_summary)
        
        return f"""Previous Conversation:
        {history_str}
        
        User's Message: {user_message}
        Conversation Context:{role_context}

        User's Word Knowledge:
        {chr(10).join(word_knowledge)}

        Use the user's knowledge and struggles to come up with conversation that matches their level. 

        If the user is struggling with basic verbs, reinforce them slowly. 
        
        ie: 
        You: שלום! מה שלומך? אני שמח לדבר איתך.
        Word Knowledge: user asked for the meaning of each word: שלום! מה שלומך? אני שמח לדבר איתך. and user asked how to say okay.
        User: אני בְּסֵדֶר

        You (ideally): למה בסדר? because this is a simple message that uses the word they just used, being minfdul that they do not know much
        Generate a natural response that continues the conversation while being mindful of the user's understanding:"""

    @staticmethod
    def create_evaluation_prompt(user_message: str) -> str:
        return """For each Hebrew word the user used, provide a ONE sentence observation about their usage.
        Focus on:
        - Correctness of usage
        - Understanding of meaning
        - Any confusion or errors
        - Grammatical accuracy

        Format:
        WORD: comment
        
        Example comments:
        - "perfect usage in context"
        - "used word incorrectly, confused with [other word]"
        - "correct usage but wrong gender"
        - "asked about meaning, needs reinforcement"
        """

@app.post("/assist/")
async def assist(input_data: QueryInput):
    user_progress = UserStorage.load_user_data(input_data.username)
    
    # Identify which words are being asked about
    word_identification_prompt = f"""You are evaluating a Hebrew learner's question.
    From this list of Hebrew words: {', '.join(FREQUENCY_LIST)}
    For each relevant word, provide a ONE sentence observation about what they're asking.
    
    Format:
    WORD: observation
    
    Example observations:
    - "asked about basic meaning, does not know word"
    - "perfect usage, asked about gender"
    - "knows meaning, confused about usage context"
    """
    
    evaluation = call_gpt_api([
        {"role": "system", "content": word_identification_prompt},
        {"role": "user", "content": input_data.query}
    ])

    # Update word history with observations
    for line in evaluation.split('\n'):
        if ':' in line:
            word, comment = line.split(':', 1)
            word = word.strip()
            comment = comment.strip()
            
            if word in FREQUENCY_LIST:
                if word not in user_progress.word_history:
                    user_progress.word_history[word] = WordHistory()
                user_progress.word_history[word] = add_observation(
                    user_progress.word_history[word],
                    comment
                )
    
    UserStorage.save_user_data(input_data.username, user_progress)

    # Generate explanation
    explanation = call_gpt_api([
        {"role": "system", "content": "You are a Hebrew language assistant. Provide clear, helpful explanations in English."},
        {"role": "user", "content": input_data.query}
    ])

    return {
        "response": explanation,
        "word_history": user_progress.word_history
    }

@app.post("/converse/", response_model=ConversationResponse)
async def converse(input_data: ConversationInput):
    user_progress = UserStorage.load_user_data(input_data.username)
    
    if input_data.role_play is not None:
        user_progress.role_play = input_data.role_play

    # Get next words to introduce
    current_words = set(user_progress.word_history.keys())
    next_words = [w for w in FREQUENCY_LIST[user_progress.current_position:] 
                 if w not in current_words][:5]

    # Generate conversation response
    response = call_gpt_api([
        {"role": "system", "content": PromptTemplate.create_system_prompt()},
        {"role": "user", "content": PromptTemplate.create_conversation_prompt(
            role_play=user_progress.role_play,
            user_message=input_data.user_message,
            word_history=user_progress.word_history,
            next_words=next_words,
            conversation_history=user_progress.conversation_history
        )}
    ])

    # Evaluate user's word usage
    evaluation = call_gpt_api([
        {"role": "system", "content": "You are a Hebrew language evaluator."},
        {"role": "user", "content": PromptTemplate.create_evaluation_prompt(input_data.user_message)}
    ])

    # Update word history based on evaluation
    for line in evaluation.split('\n'):
        if ':' in line:
            word, comment = line.split(':', 1)
            word = word.strip()
            comment = comment.strip()
            
            if word in FREQUENCY_LIST:
                if word not in user_progress.word_history:
                    user_progress.word_history[word] = WordHistory()
                user_progress.word_history[word] = add_observation(
                    user_progress.word_history[word],
                    comment
                )

    # Update conversation history
    user_progress.conversation_history.extend([
        f"User: {input_data.user_message}",
        f"Assistant: {response}"
    ])

    # Update current position
    user_progress.current_position = min(
        user_progress.current_position + len(next_words),
        len(FREQUENCY_LIST)
    )

    UserStorage.save_user_data(input_data.username, user_progress)

    return ConversationResponse(
        response=response,
        word_history=user_progress.word_history,
        next_words_to_learn=next_words,
        current_position=user_progress.current_position
    )

@app.get("/user/{username}/progress")
async def get_user_progress(username: str):
    progress = UserStorage.load_user_data(username)
    
    # Categorize words based on latest observations
    word_status = {
        "mastered": [],
        "needs_reinforcement": [],
        "new": []
    }
    
    for word, history in progress.word_history.items():
        if history.observations:
            latest_comment = history.observations[-1]["comment"].lower()
            if "perfect" in latest_comment and "asked" not in latest_comment:
                word_status["mastered"].append(word)
            else:
                word_status["needs_reinforcement"].append(word)
    
    return {
        "progress": progress,
        "stats": {
            "total_words": len(FREQUENCY_LIST),
            "mastered_words": len(word_status["mastered"]),
            "reinforcement_words": len(word_status["needs_reinforcement"]),
            "current_position": progress.current_position,
            "completion_percentage": (len(word_status["mastered"]) / len(FREQUENCY_LIST)) * 100
        },
        "word_status": word_status
    }
from typing import List, Dict, Optional, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
from pathlib import Path
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

class UserProgress(BaseModel):
    learned_words: Dict[str, float] = {}  # word: mastery_level
    role_play: Optional[str] = None
    current_position: int = 0
    conversation_history: List[str] = []

class ConversationInput(BaseModel):
    username: str
    user_message: str
    role_play: Optional[str] = None

class ConversationResponse(BaseModel):
    response: str
    updated_mastery: Dict[str, float]
    next_words_to_learn: List[str]
    current_position: int

DATA_DIR = Path("user_data")
DATA_DIR.mkdir(exist_ok=True)
FREQUENCY_LIST = get_data_list()

def update_word_mastery(current_score: float, performance_score: float, is_question: bool = False) -> float:
    """
    Update word mastery based on various conditions:
    - If user asks about a mastered word (1.0), drop to 0.1
    - If first time seeing word (0.0) and asking question, set to 0.1
    - For roleplay, weighted average with previous score having more weight
    """
    if is_question:
        if current_score >= 1.0:
            return 0.1  # Reset mastery if asking about a mastered word
        if current_score == 0.0:
            return 0.1  # First time seeing the word
        return current_score  # Let model decide other cases
    
    # For roleplay performance, weighted average
    # 70% weight to old score, 30% to new performance
    return min(1.0, (current_score * 0.7) + (performance_score * 0.3))

def categorize_words(learned_words: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
    """Categorize words based on mastery level"""
    mastered = []
    reinforcement = []
    new = []
    
    for word, score in learned_words.items():
        if score >= 1.0:
            mastered.append(word)
        elif 0.1 <= score < 0.8:
            reinforcement.append(word)
        else:
            new.append(word)
            
    return mastered, reinforcement, new

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
        1. Match the user's level and previous conversation context
        2. Use mastered words as a foundation for introducing new words
        3. Naturally incorporate ONE-TWO new Hebrew words from the provided list
        4. Match the roleplay context if provided
        5. Keep responses concise and conversational (1-2 sentences)
        6. Never directly explain word meanings - let users learn through context
        7. Never use English translations in parentheses
        8. Ensure natural conversation flow despite educational goals
        9. Talk as a friend, not a tutor"""

    @staticmethod
    def create_conversation_prompt(
        role_play: Optional[str],
        user_message: str,
        mastered_words: List[str],
        reinforcement_words: List[str],
        next_words: List[str],
        conversation_history: List[str]
    ) -> str:
        role_context = f"\nYou are {role_play} having a conversation. Maintain character but keep language appropriate to user's level." if role_play else ""
        
        history_str = "\n".join(conversation_history[-6:]) if conversation_history else "No previous conversation"
        
        return f"""Previous Conversation:
        {history_str}
        User's Message: {user_message}
        Conversation Context:{role_context}

        Word Categories:
        - Mastered words to use freely: {' '.join(mastered_words)}
        - Words needing reinforcement: {' '.join(reinforcement_words)}
        - New words to potentially introduce (use 1-2 max): {' '.join(next_words)}

        Generate a natural response that continues the conversation while incorporating appropriate words:"""

    @staticmethod
    def create_evaluation_prompt(user_message: str, response: str) -> str:
        return """As a Hebrew language evaluator, analyze this exchange and:
        1. For each Hebrew word the user used, rate their usage on a scale of 0-1.0
        2. Consider context, grammar, appropriateness of usage
        3. Be strict - a score of 1.0 means complete mastery
        4. Provide detailed reasoning for each score

        Format your response as:
        WORD: score
        REASONING: explanation
        """
class QueryInput(BaseModel):
    query: str
    username: str

@app.post("/assist/")
async def assist(input_data: QueryInput):
    user_progress = UserStorage.load_user_data(input_data.username)
    
    # Identify which words are being asked about
    word_identification_prompt = f"""Identify which Hebrew words from this list the user is asking about:
    {', '.join(FREQUENCY_LIST)}
    Return ONLY the words, comma-separated. If none, return "None"."""
    
    words = call_gpt_api([
        {"role": "system", "content": word_identification_prompt},
        {"role": "user", "content": input_data.query}
    ]).strip()

    # Update mastery scores for identified words
    if words != "None":
        for word in words.split(','):
            word = word.strip()
            current_score = user_progress.learned_words.get(word, 0.0)
            user_progress.learned_words[word] = update_word_mastery(
                current_score, 
                0.0,  # Not used for questions
                is_question=True
            )
    
    UserStorage.save_user_data(input_data.username, user_progress)

    # Generate explanation
    explanation = call_gpt_api([
        {"role": "system", "content": "You are a Hebrew language assistant. Provide clear, helpful explanations in English."},
        {"role": "user", "content": input_data.query}
    ])

    return {
        "words": None if words == "None" else words.split(','),
        "response": explanation
    }

@app.post("/converse/", response_model=ConversationResponse)
async def converse(input_data: ConversationInput):
    user_progress = UserStorage.load_user_data(input_data.username)
    
    # Update role-play setting if provided
    if input_data.role_play is not None:
        user_progress.role_play = input_data.role_play

    # Categorize words based on mastery
    mastered_words, reinforcement_words, _ = categorize_words(user_progress.learned_words)
    
    # Get next words to introduce
    next_words = FREQUENCY_LIST[user_progress.current_position:user_progress.current_position + 5]
    next_words = [w for w in next_words if w not in user_progress.learned_words]

    # Generate conversation response
    response = call_gpt_api([
        {"role": "system", "content": PromptTemplate.create_system_prompt()},
        {"role": "user", "content": PromptTemplate.create_conversation_prompt(
            role_play=user_progress.role_play,
            user_message=input_data.user_message,
            mastered_words=mastered_words,
            reinforcement_words=reinforcement_words,
            next_words=next_words,
            conversation_history=user_progress.conversation_history
        )}
    ])

    # Evaluate user's performance
    evaluation = call_gpt_api([
        {"role": "system", "content": "You are a Hebrew language evaluator."},
        {"role": "user", "content": PromptTemplate.create_evaluation_prompt(
            input_data.user_message,
            response
        )}
    ])

    # Update word mastery based on evaluation
    for line in evaluation.split('\n'):
        if line.startswith('WORD:'):
            word, score = line.replace('WORD:', '').split(',')
            word = word.strip()
            score = float(score.strip())
            
            if word in FREQUENCY_LIST:
                current_score = user_progress.learned_words.get(word, 0.0)
                user_progress.learned_words[word] = update_word_mastery(
                    current_score,
                    score,
                    is_question=False
                )

    # Update conversation history
    user_progress.conversation_history.extend([
        f"User: {input_data.user_message}",
        f"Assistant: {response}"
    ])

    # Update current position if needed
    user_progress.current_position = min(
        user_progress.current_position + len(next_words),
        len(FREQUENCY_LIST)
    )

    UserStorage.save_user_data(input_data.username, user_progress)

    return ConversationResponse(
        response=response,
        updated_mastery=user_progress.learned_words,
        next_words_to_learn=next_words,
        current_position=user_progress.current_position
    )

@app.get("/user/{username}/progress")
async def get_user_progress(username: str):
    progress = UserStorage.load_user_data(username)
    mastered, reinforcement, new = categorize_words(progress.learned_words)
    
    return {
        "progress": progress,
        "stats": {
            "total_words": len(FREQUENCY_LIST),
            "mastered_words": len(mastered),
            "reinforcement_words": len(reinforcement),
            "new_words": len(new),
            "current_position": progress.current_position,
            "completion_percentage": (len(mastered) / len(FREQUENCY_LIST)) * 100
        }
    }
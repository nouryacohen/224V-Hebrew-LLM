import json
import pandas as pd
from flask import Flask, Blueprint, request, jsonify
from data.data_processing import get_data_list  
from app.call_gpt_api import call_gpt_api

app = Flask(__name__)
database = {}  


@app.route('/practice', methods=['POST'])
def language_practicing_tab():
    from app.call_gpt_api import call_gpt_api

    data = request.json
    username = data.get("username")
    user_input = data.get("message")

    if not username or not user_input:
        return jsonify({"error": "Username and message are required"}), 400

    user_data = database.setdefault(username, {"learned_words": [], "word_status": {}, "conversation_history": []})
    conversation_history = user_data["conversation_history"]

    conversation_history.append({"role": "user", "content": user_input})

    prompt = f"""
    Simulate a conversation in Hebrew with a beginner.
    The user knows these words: {', '.join([word for word in user_data["word_status"] if user_data["word_status"][word]["practiced"]])}.
    Conversation history:
    {conversation_history}
    Add new context for the learned words and keep the conversation beginner-friendly.
    """
    try:
        bot_reply = call_gpt_api(prompt, max_tokens=150, temperature=0.7)
    except Exception as e:
        return jsonify({"error": f"Failed to call ChatGPT API: {str(e)}"}), 500

    for word in user_data["word_status"]:
        if word in bot_reply:
            user_data["word_status"][word]["seen_in_conversation"] = True

    conversation_history.append({"role": "assistant", "content": bot_reply.strip()})

    for word, status in user_data["word_status"].items():
        if status["practiced"] and status["seen_in_conversation"]:
            if word not in user_data["learned_words"]:
                user_data["learned_words"].append(word)

    return jsonify({"response": bot_reply.strip(), "conversation_history": conversation_history})


if __name__ == '__main__':
    app.run(debug=True)
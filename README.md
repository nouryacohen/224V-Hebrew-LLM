# 224V-Hebrew-LLM

Our (Brendan Reeves and Nourya Cohen's) LLM for Hebrew Language Learning

## Overview

224V-Hebrew-LLM is a language learning model designed to assist users in learning Hebrew through interactive conversations. 

## Features

- **Interactive Conversations**: Engage in dynamic conversations that adapt to your language proficiency level.
- **Role-Playing Scenarios**: Practice Hebrew in various contexts by assuming different roles.
- **Word Mastery Tracking**: Monitor your progress with detailed feedback on word usage and mastery.


## Installation

To get started:

1. Clone the repository:
   ```bash
   git clone https://github.com/nouryacohen/224V-Hebrew-LLM.git
   cd Hebrew-LLM
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

We used our own API key for the OpenAI API. In order to use this you will need to add a .env file with your own API key as follows:

GPT_API_KEY = 'insert your API key here'

### Running the Application

To start the application, use the following command:
For the backend:
```bash
python3 run.py 
```

For the frontend:

```bash
npm run dev
```
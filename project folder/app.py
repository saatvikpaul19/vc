from flask import Flask, request, jsonify, session, render_template, session
from bs4 import BeautifulSoup
import openai
from flask_cors import CORS
import requests
import pandas as pd
import os
from dotenv import load_dotenv
import secrets

load_dotenv()
app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

CORS(app, supports_credentials=True)
openai.api_key = os.getenv("OPENAI_API_KEY")

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.route('/')
def index():
    return render_template('index.html', run_python_code=True)


def scrape_website(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        relevant_info = soup.find('div', class_='visa-info').text
        return relevant_info
    except Exception as e:
        return None

def get_openai_response(prompt):
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=150
        )
        return response['choices'][0]['text'].strip()
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return "I'm sorry, I couldn't understand the query."

def build_prompt(conversation_history):
    prompt = ""
    for entry in conversation_history:
        prompt += f"User: {entry['user_query']}\nBot: {entry['bot_response']}\n"
        if 'terms' in entry:
            prompt += f"Terms: {' '.join(entry['terms'])}\n"
    return prompt

def extract_terms(response):
    terms = [word.lower() for word in response.split()]
    return terms

def save_to_excel(conversation_history):
    try:
        excel_file_path = 'conversation_history.xlsx'
        df = pd.read_excel(excel_file_path, sheet_name='Sheet1', engine='openpyxl')
    except FileNotFoundError:
        print("Excel file not found. Creating a new file.")
        df = pd.DataFrame()

    new_data = pd.DataFrame(conversation_history)
    df = df.append(new_data, ignore_index=True)

    with pd.ExcelWriter(excel_file_path, engine='xlsxwriter', mode='w') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

    with pd.ExcelWriter(excel_file_path, engine='xlsxwriter', mode='w') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

@app.route('/get_response', methods=['POST', 'GET'])
def get_response():
    try:
        if request.method == 'POST':
            data = request.get_json()
            user_query = data['user_query']

            if 'conversation_history' not in session:
                session['conversation_history'] = []

            conversation_history = session['conversation_history']

            prompt = build_prompt(conversation_history)
            prompt += f"User: {user_query}\n"

            if any(keyword in user_query.lower() for keyword in ["immigration", "migrate", "entry", "exit", "stay", "residence", "schengen", "embassy", "consulate", "citizenship", "nationality", "refugee", "asylum", "sponsorship", "sponsor", "green card", "permanent residency","pr", "work permit", "employment authorization", "study permit", "student visa", "tourist attractions", "places to visit", "health insurance", "medical requirements", "travel restrictions", "covid-19 guidelines", "consular services", "diplomatic mission", "overstay", "visa violation", "appeal", "reconsideration", "entry requirements", "exit requirements", "visa", "requirements", "apply", "application", "type", "category", "process", "procedure", "document", "paperwork", "fee", "cost", "interview", "appointment", "eligibility", "qualifications", "status", "update", "duration", "timeline", "rejection", "denied", "validity", "expire", "extension", "renew", "multiple entry", "single entry", "passport", "travel document", "country", "destination", "us", "usa" , "form"]):
                website_url = 'https://www.beyondbharatconsultancy.com/'
                web_scraped_response = scrape_website(website_url)

                if web_scraped_response:
                    response = web_scraped_response
                else:
                    dynamic_prompt = build_prompt(conversation_history)
                    dynamic_prompt += f"User: {user_query}\n"
                    response = get_openai_response(dynamic_prompt)

                terms = extract_terms(response)
                prompt += f"Terms: {' '.join(terms)}\n"

            else:
                response = "I can only provide information on visa-related queries."
                terms = None

            conversation_history.append({'user_query': user_query, 'bot_response': response, 'terms': terms})
            save_to_excel(conversation_history)

            session.modified = True
            return jsonify({'response': response})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(debug=True)

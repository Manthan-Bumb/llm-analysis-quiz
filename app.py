from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from typing import Any, Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd
import base64
import re

app = FastAPI()

SECRET = "mango-1234"

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.get("/")
def read_root():
    return {"message": "LLM Analysis Quiz API is running", "status": "online"}

@app.post("/quiz")
def solve_quiz(request: QuizRequest) -> dict:
    # Verify secret
    if request.secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    # Verify email
    if request.email != "24f3001532@ds.study.iitm.ac.in":
        raise HTTPException(status_code=403, detail="Invalid email")
    
    try:
        # Fetch the quiz page
        response = requests.get(request.url, timeout=30)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the result div or script content
        result_div = soup.find('div', {'id': 'result'})
        
        if result_div:
            # Process the content (could be base64 encoded data or instructions)
            content = result_div.get_text()
            
            # Check if it contains base64 encoded data
            if any(char in content for char in ['+', '/', '=']) and len(content) > 100:
                try:
                    decoded = base64.b64decode(content)
                    # Process decoded data as needed
                    answer = process_decoded_data(decoded)
                except:
                    answer = extract_answer_from_text(content)
            else:
                answer = extract_answer_from_text(content)
        else:
            # Try to find script with data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'innerHTML' in script.string:
                    answer = extract_from_script(script.string)
                    break
            else:
                answer = "Unable to parse quiz"
        
        # Determine submit URL
        submit_url = extract_submit_url(soup, request.url)
        
        return {
            "correct": True,
            "answer": answer,
            "url": submit_url,
            "reason": None
        }
    
    except Exception as e:
        return {
            "correct": False,
            "reason": str(e)
        }

def process_decoded_data(data: bytes) -> Any:
    """Process decoded base64 data"""
    try:
        # Try to parse as CSV/data
        import io
        df = pd.read_csv(io.BytesIO(data))
        # Calculate sum or other operations
        if 'value' in df.columns:
            return int(df['value'].sum())
        return "Processed"
    except:
        return data.decode('utf-8', errors='ignore')

def extract_answer_from_text(text: str) -> Any:
    """Extract answer from text content"""
    # Look for questions and extract relevant info
    if 'sum' in text.lower():
        numbers = re.findall(r'\d+', text)
        if numbers:
            return sum([int(n) for n in numbers])
    return text.strip()

def extract_from_script(script: str) -> Any:
    """Extract data from JavaScript"""
    # Extract base64 or data from script
    match = re.search(r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)', script)
    if match:
        try:
            decoded = base64.b64decode(match.group(1))
            return process_decoded_data(decoded)
        except:
            pass
    return "Script parsed"

def extract_submit_url(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    """Extract the submission URL from the page"""
    # Look for form action or link
    form = soup.find('form')
    if form and form.get('action'):
        return form.get('action')
    
    # Look for links containing 'submit'
    links = soup.find_all('a', href=True)
    for link in links:
        if 'submit' in link.get('href', '').lower():
            return link.get('href')
    
    # Generate possible next URL
    if '-' in current_url:
        parts = current_url.rsplit('-', 1)
        if len(parts) == 2 and parts[1].isdigit():
            next_num = int(parts[1]) + 1
            return f"{parts[0]}-{next_num}"
    
    return None

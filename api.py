# api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from rag_model import RAGModel  # Ensure this import points to where your RAGModel class is defined
app = FastAPI()
# CORS POLICY
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Initialize your RAGModel
rag_model = RAGModel()

class QueryModel(BaseModel):
    query: str

import re

def clean_text(text):
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    # Remove manuscript lines
    text = re.sub(r'Manuscript\s[A-Za-z]+\s', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

# Example usage
ugly_text = "Your text here"
cleaned_text = clean_text(ugly_text)
print(cleaned_text)


@app.post("/generate-response/")
async def generate_response(query_model: QueryModel):
    try:
        response,question = rag_model.generate_response(query_model.query)
         # Clean the response string by removing \n and \t characters
        clean_response = response.replace('\n', ' ').replace('\t', ' ')
        # Optionally, further clean by removing multiple spaces with a single space
        clean_response = ' '.join(clean_response.split())
        clean_response=clean_text(clean_response)
        return {"response": clean_response,"question": question}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env file
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. Add it to your .env file."
    )

# Configure Gemini
genai.configure(api_key=api_key)

# Create model
model = genai.GenerativeModel("gemini-2.5-flash")

# Ask a question
response = model.generate_content(
    "How can farmers prevent tomato late blight?"
)

print("\n===== GEMINI RESPONSE =====\n")
print(response.text)
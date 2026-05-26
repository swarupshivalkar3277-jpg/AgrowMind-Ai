import google.generativeai as genai

genai.configure(api_key="YOUR_KEY")

model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content(
    "How can farmers prevent tomato late blight?"
)

print(response.text)
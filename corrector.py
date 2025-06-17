from openai import OpenAI
import argparse
import os

client = OpenAI(
  api_key=os.getenv("OPENAI_API_KEY"),
  organization=os.getenv("OPENAI_ORGANIZATION")
)

parser = argparse.ArgumentParser(
    description="SRT corrector."
)

parser.add_argument("filename", type=str, help="Path to the SRT file")
parser.add_argument("--keywords", type=str, help="Keywords for the conversation", default="")
args = parser.parse_args()

def correct_text(text, context):
    system_prompt = f"Fix any errors in the input <text-to-correct> while preserving the original meaning. Only output the corrected text without any explanations."
    user_prompt = f"""
    This is a conversation about: {args.keywords}
    
    {context}
    <text-to-correct>
    {text}
    </text-to-correct>
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()

with open(args.filename, "r", encoding="utf-8") as file:
  text = file.readlines()
  context = []
  for idx in range(0, len(text)):
    if (text[idx].strip().includes("-->")):
      corrected_text = correct_text(text[idx+1].strip(), context)
      context.append(corrected_text)
      if (len(context) > 5):
        context.pop(0)
      output = f"""
      {text[idx-1].strip()}
      {text[idx].strip()}
      {corrected_text}
      """
      print(output)
  

import pandas as pd

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import PyPDF2
from io import BytesIO
import google.generativeai as genai



app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests


genai.configure(api_key="AIzaSyC-RrZSvjas1tSj5NJoZBWcf3kDtJTmAxo")

BASE_URL = "https://www.screener.in/company/{}/consolidated/"
def extract_text_from_pdf(pdf_url):
    """Downloads a PDF from a URL and extracts the text."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Referer": "https://www.screener.in/"
        }

        response = requests.get(pdf_url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        pdf_file = BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() or "" #handle if a page has no text.

        return text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching PDF: {e}")
        return None
    except PyPDF2.errors.PdfReadError as e:
        print(f"Error reading PDF: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occured: {e}")
        return None

def summarize_concall(pdf_url):
    """Summarizes a concall PDF from a URL."""
    transcript_text = extract_text_from_pdf(pdf_url)

    #print(transcript_text)

    if not transcript_text:
        return "Failed to extract text from PDF."

    prompt = f"""
    As a **seasoned financial analyst**, analyze the following **company earnings call (concall) transcript** in detail and provide a **structured, data-driven summary** with clear, concise insights. Your summary should be well-formatted, engaging, and easy to understand. Focus on the following key aspects:

    ### **1️⃣ Management Guidance & Strategic Outlook**  
    - What are the company’s **growth projections**, revenue targets, and **future expectations** for the next quarters and fiscal year?  
    - Highlight any **strategic shifts, diversification plans, or key initiatives** mentioned by the management.  
    - Identify **specific geographies, sectors, or market segments** the company is targeting for expansion.  

    ### **2️⃣ Key Risks & Challenges**  
    - What **operational, financial, or macroeconomic risks** were discussed?  
    - Are there any concerns regarding **supply chain disruptions, regulatory changes, or competitive pressures**?  
    - Mention risks related to **profitability, cost structures, or demand volatility**.  

    ### **3️⃣ Capex Plans & Investment Strategy**  
    - Summarize the company’s **capital expenditure (Capex) plans and key investment areas**.  
    - Are there any new **manufacturing units, technology upgrades, or global expansion plans**?  
    - Evaluate whether these investments align with the company’s **long-term growth vision**.  

    ### **4️⃣ Financial Performance & Revenue Guidance**  
    - Provide **projections** for revenue, profit margins, and other key financial indicators for the next quarter and fiscal year.  
    - Summarize **EBITDA, operating margins, and cash flow trends**.  
    - Highlight any **changes in financial guidance**, cost management insights, or forex impact.  

    ### **5️⃣ Operational Efficiency & Cost Optimization**  
    - What measures are being taken to **enhance efficiency and reduce costs**?  
    - Mention any **automation, digitization, or operational improvements** aimed at boosting profitability.  

    ### **6️⃣ Competitive Landscape & Industry Trends**  
    - Analyze the company’s **market positioning relative to competitors**.  
    - Highlight any **industry trends or emerging opportunities/threats** that could impact growth.  

    ### **7️⃣ ESG & Sustainability Initiatives**  
    - List any key **Environmental, Social, and Governance (ESG) initiatives** mentioned.  
    - Are there sustainability goals, **green initiatives, or compliance measures** discussed?  

    ---

    📌 **Formatting Guidelines:**  
    - Use **clear subheadings, bullet points, and structured paragraphs** for readability.  
    - Highlight **key financial figures** in bold.  
    - Keep the tone **professional yet easy to comprehend**.  

    📜 **Transcript:**  
    {transcript_text}
    """

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    # Format the summary as HTML (example - you can refine this)
    formatted_summary = response.text.replace('\n', '<br>')
    formatted_summary = formatted_summary.replace('###', '<p class="section-heading">')
    formatted_summary = formatted_summary.replace('**', '<b>')
    formatted_summary = formatted_summary.replace('*', '<li>')
    formatted_summary = formatted_summary.replace('---', '<hr>')
    formatted_summary = formatted_summary.replace('</p>', '</p><br>')

    return formatted_summary

#Example static company data, replace with database or api call.
# companies = [
#     {"id": 1, "name": "Reliance Industries", "ticker": "RELIANCE"},
#     {"id": 2, "name": "Tata Consultancy Services", "ticker": "TCS"},
#     {"id": 3, "name": "Infosys", "ticker": "INFY"},
#     {"id": 4, "name": "Aadhar Housing Finance", "ticker" : "AADHARHFC"},
#     {"id": 5, "name": "Concord Enviro System", "ticker": "CEWATER"},
#     {"id": 6, "name": "Bharat Electronics Limited", "ticker": "BEL"},
#     {"id": 7, "name": "Ventive Hospitality Ltd", "ticker": "VENTIVE"},
#     {"id": 8, "name": "Technocraft Industries (India) Ltd", "ticker": "TIIL"},
#     {"id": 9, "name": "Swiggy", "ticker": "SWIGGY"}
# ]


file_path = "nse_listed_companies.csv"  # Update the path to the file you download
df = pd.read_csv(file_path)

# Create list of dictionaries in the required format
companies = []
for idx, row in df.iterrows():
    companies.append({
        "id": idx + 1,
        "name": row["NAME OF COMPANY"],
        "ticker": row["SYMBOL"]
    })

@app.route('/api/companies', methods=['GET'])
def get_companies():
    query = request.args.get('query', '').lower()
    filtered_companies = [c for c in companies if query in c['name'].lower()]
    return jsonify(filtered_companies)

@app.route('/api/concalls/<ticker>', methods=['GET'])
def get_concalls(ticker):
    url = BASE_URL.format(ticker)
    output_folder = f"concall_docs/{ticker}"
    os.makedirs(output_folder, exist_ok=True)
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"⚠️ Error fetching company page: {e}"}), 500

    html_file_path = 'file.html'
    with open(html_file_path, "w") as f:
        f.write(response.text)

    # Load the HTML content
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all list items (li tags)
    list_items = soup.find_all('li', class_='flex flex-gap-8 flex-wrap')

    # Extract the quarters and links with title "Raw Transcript"
    results = []

    for item in list_items:
        try:
            quarter_div = item.find('div', class_='ink-600 font-size-15 font-weight-500 nowrap')
            quarter = quarter_div.text.strip() if quarter_div else "Unknown Quarter"
            transcript_link = item.find('a', title='Raw Transcript')
            if transcript_link:
                link_url = transcript_link['href']
                results.append({'quarter': quarter, 'link': link_url})
        except Exception as e:
            print(f"Error parsing item: {e}")
            continue

    if not results:
        return jsonify({"error": f"⚠️ No transcripts found."}), 200

    return jsonify(results)

@app.route('/api/summary', methods=['POST'])
def get_summary():
    data = request.get_json()
    pdf_url = data.get('pdf_url')
    if not pdf_url:
        return jsonify({"error": "PDF URL is required"}), 400

    try:
        summary = summarize_concall(pdf_url)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": f"Error generating summary: {e}"}), 500


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app.run(debug=True, port=5000)
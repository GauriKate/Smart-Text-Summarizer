
# Smart Text Summarizer | NLP-Based Text Summarization

A web-based text-processing application built with Python and Flask. It helps users generate concise summaries from text and PDF documents. It also provides additional features such as language detection, translation, sentiment analysis, text-to-speech, PDF generation, and email notifications.

**Key Features**
- Summarize user-provided text.
- Extract text from PDF documents and generate summaries.
- Detect the language of input text.
- Translate text using the Google Translate API integration.
- Perform sentiment analysis.
- Convert summaries into audio using text-to-speech.
- Generate PDF output.
- Send summarized content through email.

**Technologies Used**
- Backend: Python, Flask
- NLP Libraries: spaCy, NLTK, TextBlob, Summa
- Translation: Google Translate API
- Text-to-Speech: gTTS
- Other Features: PDF generation, email integration

**How It Works**
1. The user enters text or provides a PDF through the web interface.
2. The application extracts and preprocesses the text.
3. The summarization component generates a shorter version of the content.
4. Additional NLP features detect language, translate text, or analyse sentiment.
5. The summary can be converted into audio or generated as a PDF.
6. Users can send the summarized content through the email feature.

**Getting Started**

**Prerequisites**
- Python installed
- Git
- Required API credentials and email configuration

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/GauriKate/Smart-Text-Summarizer.git
```

### 2. Navigate to the Project Folder

```bash
cd Smart-Text-Summarizer
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

### 4. Activate the Virtual Environment

**Windows:**

```powershell
venv\Scripts\activate
```

### 5. Install Dependencies

If a requirements.txt file is available:

```bash
pip install -r requirements.txt
```

### 6. Configure Email and API Settings

Configure the email account settings and any API credentials required by the application.

**Important:** Do not upload email passwords, app passwords, API keys, or other sensitive information to GitHub. Use environment variables or a local configuration file excluded from Git.

## Running the Application

If your Flask entry-point file is app.py, run:

```bash
python app.py
```

Open the local URL shown in the terminal.

**My Contribution**

Worked on text extraction and preprocessing, implementing the summarization workflow, integrating language detection, translation and sentiment analysis features, and adding PDF generation, text-to-speech, and email functionality to the Flask application.

**Future Improvements**
- Improve summary quality for different document types.
- Add support for more input formats.
- Improve handling of long documents and large PDF files.
- Add clearer validation and error messages.


import html
import io
import os
import random
import re
import smtplib
import ssl
import uuid

from email.message import EmailMessage
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import spacy
from dotenv import load_dotenv
from flask import Flask, abort, flash, render_template, request
from gtts import gTTS
from langdetect import detect
from nltk.tokenize.punkt import PunktSentenceTokenizer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from summa.summarizer import summarize as summa_summarize
from textblob import TextBlob
from werkzeug.utils import secure_filename


# ------------------ Configuration ------------------

BASE_DIR = Path(__file__).resolve().parent

# Load .env from the same directory as app.py
load_dotenv(BASE_DIR / ".env", override=True)

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

UPLOAD_FOLDER = BASE_DIR / "uploads"
STATIC_FOLDER = BASE_DIR / "static"

UPLOAD_FOLDER.mkdir(exist_ok=True)
STATIC_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


# ------------------ Load spaCy Model ------------------

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None
    print(
        "WARNING: spaCy model 'en_core_web_sm' is not installed. "
        "Keyword and named entity extraction will be unavailable."
    )


# ------------------ Helper Functions ------------------

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def extract_text_from_file(file_storage):
    """Extract text from TXT, PDF, or DOCX files."""

    filename = secure_filename(file_storage.filename or "")

    if not filename or not allowed_file(filename):
        raise ValueError("Please upload a TXT, PDF, or DOCX file.")

    data = file_storage.read()

    if not data:
        raise ValueError("The uploaded file is empty.")

    extension = filename.rsplit(".", 1)[1].lower()

    if extension == "txt":
        return data.decode("utf-8-sig", errors="replace").strip()

    if extension == "pdf":
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(data))

        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        ).strip()

    if extension == "docx":
        import docx

        document = docx.Document(io.BytesIO(data))

        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        ).strip()

    raise ValueError("Unsupported file type.")


def detect_language(text):
    try:
        return detect(text)
    except Exception:
        return "en"


def summarize_text(text, ratio=0.2):
    """Generate an extractive summary using Summa/TextRank."""

    try:
        sentence_count = len(
            PunktSentenceTokenizer().tokenize(text)
        )

        if sentence_count < 3:
            flash(
                "Text is too short to summarize effectively. "
                "The original text is shown.",
                "warning"
            )
            return text

        ratio = max(0.05, min(float(ratio), 0.8))

        return summa_summarize(text, ratio=ratio) or text

    except Exception as exc:
        app.logger.exception("Summarization failed")
        flash(f"Summarization failed: {exc}", "error")
        return text


def generate_tts(text, lang="en"):
    """Generate an MP3 audio file for the summary."""

    if not text.strip():
        return None

    filename = f"summary_{uuid.uuid4().hex}.mp3"
    audio_path = STATIC_FOLDER / filename

    try:
        language_code = lang if lang and lang != "unknown" else "en"

        gTTS(
            text=text,
            lang=language_code
        ).save(str(audio_path))

        return filename

    except Exception as exc:
        app.logger.exception("Text-to-speech generation failed")
        flash(
            f"Text-to-speech generation failed: {exc}",
            "warning"
        )
        return None


def extract_keywords(text):
    if nlp is None:
        return []

    try:
        doc = nlp(text)

        keywords = [
            token.lemma_.lower()
            for token in doc
            if token.pos_ in ("NOUN", "PROPN")
            and not token.is_stop
            and token.is_alpha
        ]

        return list(dict.fromkeys(keywords))[:10]

    except Exception:
        app.logger.exception("Keyword extraction failed")
        return []


def generate_summary_title(text):
    if nlp is None:
        return "Text Summary"

    try:
        doc = nlp(text.strip().replace("\n", " "))

        keywords = [
            token.lemma_.title()
            for token in doc
            if token.pos_ == "NOUN"
            and not token.is_stop
            and token.is_alpha
        ]

        keywords = list(dict.fromkeys(keywords))[:5]

        organizations = [
            entity.text.strip()
            for entity in doc.ents
            if entity.label_ == "ORG"
        ]

        main_topic = (
            organizations[0]
            if organizations
            else (keywords[0] if keywords else "Insight")
        )

        templates = [
            f"{main_topic} Insights",
            f"{main_topic} Highlights",
            f"Inside {main_topic}",
            f"{main_topic} Overview",
            f"About {main_topic}",
            f"{main_topic} Brief",
            f"{main_topic} Summary"
        ]

        return random.choice(templates)

    except Exception:
        app.logger.exception("Title generation failed")
        return "Text Summary"


def analyze_sentiment(text):
    try:
        polarity = TextBlob(text).sentiment.polarity

        if polarity > 0.1:
            return "Positive"

        if polarity < -0.1:
            return "Negative"

        return "Neutral"

    except Exception:
        return "Unknown"


def extract_named_entities(text):
    if nlp is None:
        return []

    try:
        clean_text = re.sub(
            r"\[\d+(?:\]\[\d+)*\]",
            "",
            text
        )

        clean_text = re.sub(
            r"\[\d+\]",
            "",
            clean_text
        )

        doc = nlp(clean_text)

        return sorted({
            f"{entity.text} ({entity.label_})"
            for entity in doc.ents
        })

    except Exception:
        app.logger.exception("Named entity extraction failed")
        return []


# ------------------ PDF Generation ------------------

def create_pdf(summary_text, title):
    """Generate a PDF containing the summary."""

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    safe_title = xml_escape(title)

    safe_summary = xml_escape(
        summary_text
    ).replace("\n", "<br/>")

    elements = [
        Paragraph(
            f"<b>{safe_title}</b>",
            styles["Heading1"]
        ),
        Spacer(1, 12),
        Paragraph(
            safe_summary,
            styles["Normal"]
        )
    ]

    document.build(elements)

    return buffer.getvalue()


# ------------------ SMTP Helper ------------------

def send_smtp_message(message):
    """
    Connect to Gmail using port 587 and STARTTLS.
    This is the connection method confirmed by the standalone test.
    """

    with smtplib.SMTP(
        SMTP_SERVER,
        587,
        timeout=30
    ) as server:

        server.ehlo()

        server.starttls(
            context=ssl.create_default_context()
        )

        server.ehlo()

        server.login(
            EMAIL_USER,
            EMAIL_PASS
        )

        server.send_message(message)


# ------------------ Email Sending ------------------

def send_email(to_addr, summary_text, title, audio_filename=None):
    """Send summary email with PDF and optional audio attachment."""

    if not EMAIL_USER or not EMAIL_PASS:
        flash(
            "Email is not configured. Check EMAIL_USER and EMAIL_PASS "
            "in your .env file.",
            "error"
        )
        return False

    if not to_addr or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+",
        to_addr
    ):
        flash("Please enter a valid email address.", "error")
        return False

    word_count = len(summary_text.split())

    message = EmailMessage()

    message["Subject"] = "Your Text Summary"
    message["From"] = EMAIL_USER
    message["To"] = to_addr

    message.set_content(
        f"{title}\n\n"
        f"{summary_text}\n\n"
        f"Sent by Text Summarizer ({word_count} words)"
    )

    safe_title = html.escape(title)

    safe_summary = html.escape(
        summary_text
    ).replace("\n", "<br>")

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>{safe_title}</h2>
        <p>{safe_summary}</p>
        <hr>
        <small>
            Sent by <em>Text Summarizer</em> - {word_count} words
        </small>
      </body>
    </html>
    """

    message.add_alternative(
        html_body,
        subtype="html"
    )

    try:
        # Attach PDF summary
        pdf_data = create_pdf(
            summary_text,
            title
        )

        message.add_attachment(
            pdf_data,
            maintype="application",
            subtype="pdf",
            filename="summary.pdf"
        )

        # Attach audio file if available
        if audio_filename:
            audio_path = STATIC_FOLDER / audio_filename

            if audio_path.is_file():
                with audio_path.open("rb") as audio_file:

                    message.add_attachment(
                        audio_file.read(),
                        maintype="audio",
                        subtype="mpeg",
                        filename="summary.mp3"
                    )

        # Send email using port 587 + STARTTLS
        send_smtp_message(message)

        flash(
            f"Summary emailed successfully to {to_addr}.",
            "success"
        )

        return True

    except smtplib.SMTPAuthenticationError:
        app.logger.exception("Gmail authentication failed")

        flash(
            "Email authentication failed. Check your Gmail address "
            "and App Password.",
            "error"
        )

    except Exception as exc:
        app.logger.exception("Email sending failed")

        flash(
            f"Unable to send email: {exc}",
            "error"
        )

    return False


# ------------------ Flask Routes ------------------

@app.route("/", methods=["GET", "POST"])
def index():

    summary = ""
    keywords = []
    audio_filename = ""
    language = ""
    summary_title = ""
    named_entities = []
    sentiment_result = ""

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        input_text = request.form.get(
            "input_text",
            ""
        ).strip()

        upload = request.files.get("file")

        # Validate summary ratio
        try:
            ratio = float(
                request.form.get("summary_ratio", 0.2)
            )

            ratio = max(
                0.05,
                min(ratio, 0.8)
            )

        except (TypeError, ValueError):

            ratio = 0.2

            flash(
                "Invalid summary length selected. "
                "The default setting was used.",
                "warning"
            )

        # Extract text from uploaded file
        if upload and upload.filename:

            try:
                input_text = extract_text_from_file(upload)

            except Exception as exc:
                app.logger.exception("File extraction failed")

                flash(
                    f"Could not read the uploaded file: {exc}",
                    "error"
                )

                input_text = ""

        # Process input text
        if input_text:

            language = detect_language(input_text)

            summary = summarize_text(
                input_text,
                ratio
            )

            keywords = extract_keywords(summary)

            audio_filename = generate_tts(
                summary,
                lang=language
            )

            summary_title = generate_summary_title(
                input_text
            )

            named_entities = extract_named_entities(
                input_text
            )

            sentiment_result = analyze_sentiment(
                input_text
            )

            # Send summary by email if an address is provided
            if email:

                send_email(
                    email,
                    summary,
                    summary_title,
                    audio_filename
                )

        else:

            flash(
                "Please enter text or upload a supported file.",
                "error"
            )

    return render_template(
        "index.html",
        summary=summary,
        keywords=keywords,
        audio_path=audio_filename,
        language=language,
        summary_title=summary_title,
        entities=named_entities,
        sentiment=sentiment_result
    )


# ------------------ Optional Test Email Route ------------------

@app.route("/test_email", methods=["POST"])
def test_email():

    if os.getenv(
        "ENABLE_TEST_EMAIL",
        "false"
    ).lower() != "true":

        abort(404)

    if not EMAIL_USER or not EMAIL_PASS:
        return "Email credentials are not configured.", 500

    test_message = EmailMessage()

    test_message["Subject"] = "Test Email from Flask"
    test_message["From"] = EMAIL_USER
    test_message["To"] = EMAIL_USER

    test_message.set_content(
        "This is a test email from the Text Summarizer project."
    )

    try:

        # Use the same working SMTP helper
        send_smtp_message(test_message)

        return "Test email sent successfully."

    except Exception:
        app.logger.exception("Test email failed")

        return (
            "Test email failed. Check the Flask terminal for details.",
            500
        )


# ------------------ Run Flask Application ------------------

if __name__ == "__main__":

    debug_mode = (
        os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )

    app.run(
        debug=debug_mode,
        use_reloader=False
    )

import logging
import os
import re

from docx import Document
from io import BytesIO
from fastapi import HTTPException
import gdown
import tempfile

import google.generativeai as genai
import requests
from fpdf import FPDF

from app.core.settings import settings

logger = logging.getLogger(__name__)


# Configure Gemini API (ensure you use environment variables)
GEMINI_API_KEY = os.getenv("AIzaSyBf6XLpCYFTdVG5p7YiouYxEpkGAKYqmJQ")  # Store securely!
genai.configure(api_key=GEMINI_API_KEY)


class OnePagerPDF(FPDF):
    def __init__(self, header_text=""):
        super().__init__()
        self.header_text = header_text  # Store the class name for the header

    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, f"{self.header_text}: Weekly Class Newsletter", ln=1, align="C")
        self.ln(10)

    def add_section(self, title, content):
        self.set_font("Arial", "B", 14)
        self.set_text_color(0, 102, 204)
        self.cell(0, 10, title, ln=1)
        self.ln(5)
        self.set_font("Arial", "", 12)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 10, content)
        self.ln(10)




def extract_and_summarize(file_url):
    """
    Downloads a .docx file from Google Drive using gdown, saves it to a temporary file,
    and extracts the required fields.
    """
    try:
        # Save the content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            temp_file_path = temp_file.name

        # Use gdown to download the file
        try:
            gdown.download(url=file_url, output=temp_file_path, quiet=False)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download file with gdown: {str(e)}")

        # Process the .docx file
        try:
            doc = Document(temp_file_path)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to process the file as a .docx: {str(e)}"
            )

        # Extract data from the document
        extracted_data = {
            "Name of the Class": "Unknown Class",
            "Last week’s Activities": "No activities listed.",
            "Next week’s Activities": "No plans listed.",
            "Special Announcement": "No announcements.",
        }

        for table in doc.tables:
            for row in table.rows:
                if len(row.cells) >= 2:
                    key = row.cells[0].text.strip()
                    value = row.cells[1].text.strip()
                    if key in extracted_data:
                        extracted_data[key] = value

        # Clean up the temporary file
        os.remove(temp_file_path)

        return (
            extracted_data["Name of the Class"],
            extracted_data["Last week’s Activities"],
            extracted_data["Next week’s Activities"],
            extracted_data["Special Announcement"],
        )

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        )

    
def clean_markdown(text):
    """Remove markdown symbols and extra spaces."""
    text = re.sub(r"\*\*|\*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    replacements = {
    "\u2019": "'",  # Right single quotation mark to ASCII apostrophe
    "\u2013": "-",  # En dash to hyphen
    "\u2014": "-",  # Em dash to hyphen
    "\u201c": '"',  # Left double quotation mark to ASCII double quote
    "\u201d": '"',  # Right double quotation mark to ASCII double quote
}
    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)
    return text


def calling_gemini(prompt):
    """Summarize text using Gemini API."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text


def narrative_generator(past_activities, furure_plans, announcement):
    """Extracts key sections from a document and summarizes them."""
    try:
        past_activities = calling_gemini(
            f"You are now helping a teacher writing a newsletter to report about the activities of the class to parents, write a nice narrative for the class activities of last week. Only make use of the information that you are given and keep it moderate:\n\n{past_activities}"
        )
        furure_plans = calling_gemini(
            f"You are now helping a teacher writing a newsletter to report about the activities of the class to parents, write a nice narrative for the class activities of next week. Only make use of the information that you are given and keep it moderate:\n\n{furure_plans}"
        )
        announcement = calling_gemini(
            f"You are now helping a teacher writing a newsletter to report about the activities of the class to parents, write a nice narrative for this announcement. Only make use of the information that you are given and keep it moderate:\n\n{announcement}"
        )

        return (
            clean_markdown(past_activities),
            clean_markdown(furure_plans),
            clean_markdown(announcement),
        )
    except Exception as e:
        print(f"Error processing extracted text: {e}")
        return (
            "Error extracting highlights.",
            "Error extracting activities.",
            "Error extracting future_plan.",
        )


def generate_overview_short(past_activities, future_plan, announcement):
    """Generates a concise class newsletter overview."""
    prompt = (
        f"You are a teacher making a weekly report about a class"
        f"Here I need you to write the overview of the report "
        f"Generate a concise, high-level overview for a class newsletter. "
        f"Summarize key focus areas without listing details: {past_activities}, {future_plan}, {announcement}."
    )
    return clean_markdown(calling_gemini(prompt))


def fetch_file(url):
    """Fetches lesson plan content from a given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Error fetching lesson plan: {e}")


def create_newsletter_pdf(name, overview_text, table_data, filename="newsletter.pdf"):
    """
    Creates a PDF document from the generated lesson content using sections.
    :param name: The name of the class.
    :param overview_text: The overview of the newsletter.
    :param table_data: A dictionary with section titles as keys and content as values.
    :param filename: The name of the output PDF file.
    :return: The path to the saved PDF file.
    """
    # Initialize the PDF with the class name as the header
    pdf = OnePagerPDF(name)
    pdf.add_page()

    # Add the overview section
    pdf.add_section("Overview", clean_markdown(overview_text))

    # Add each section dynamically based on the table data
    for title, content in table_data.items():
        pdf.add_section(title, clean_markdown(content))

    # Save the PDF
    full_path = os.path.join(settings.media_dir_static, filename)
    pdf.output(full_path, "F")

    return full_path


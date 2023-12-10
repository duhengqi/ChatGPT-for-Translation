import argparse
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import concurrent.futures
from tqdm import tqdm
from openai import OpenAI
import requests
import trafilatura
import pdfplumber
from utils.bilingual_txt_to_docx import create_bilingual_docx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff
from concurrent.futures import as_completed
ALLOWED_FILE_TYPES = [
    ".pdf",
]

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def translate(key, target_language, text, use_azure=False, api_base="", deployment_name="", options=None):
    client = OpenAI(
      api_key=key,
      base_url="https://api.openai-proxy.org/v1"
    )
    # Set up the prompt
    messages = [{
        'role': 'system',
        'content': 'You are an expert in translation of the Linux kernel.'
    }, {
        "role":
        "user",
        "content":
        f"Translate the following text into {target_language}. Retain the original format. Return only the translation and nothing else:\n{text}",
    }]
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=messages
    )

    t_text = completion.choices[0].message.content.encode("utf8").decode()
    return t_text

def translate_text_file(paragraphs, options):
    OPENAI_API_KEY = options.openai_key
    # Create a list to hold your translated_paragraphs. We'll populate it as futures complete.
    translated_paragraphs = [None for _ in paragraphs]

    # Submit your translation tasks
    futures = []
    with ThreadPoolExecutor(max_workers=options.num_threads) as executor:
        for idx, text in enumerate(paragraphs):
            future = executor.submit(
                translate,
                OPENAI_API_KEY,
                options.target_language,
                text,
                options.use_azure,
                options.azure_endpoint,
                options.azure_deployment_name,
                options=options
            )
            futures.append((idx, future))
        # Iterate over the futures as they complete.
        for future in tqdm(as_completed([future for idx, future in futures]), total=len(paragraphs), desc="Translating paragraphs", unit="paragraph"):
            for idx, f in futures:
                if f == future:
                    try:
                        translated_paragraphs[idx] = future.result().strip()
                    except Exception as e:
                        print(f"An error occurred during translation: {e}")
                        translated_paragraphs[idx] = ""  # or however you want to handle errors

    return translated_paragraphs

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser()
    arguments = [
        ("--input_path", {"type": str,
         "help": "input file or folder to translate"}),
        ("--openai_key", {"type": str,
         "default": "", "help": "OpenAI API key"}),
        ("--model", {"type": str, "default": "gpt-3.5-turbo",
         "help": "Model to use for translation, e.g., 'gpt-3.5-turbo' or 'gpt-4'"}),
        ("--num_threads", {"type": int, "default": 10,
         "help": "number of threads to use for translation"}),
        ("--target_language", {"type": str, "default": "Simplified Chinese",
         "help": "target language to translate to"}),
        ("--only_process_this_file_extension",
         {"type": str, "default": "", "help": "only process files with this extension"}),
        ("--use_azure", {"action": "store_true", "default": False,
         "help": "Use Azure OpenAI service instead of OpenAI platform."}),
        ("--azure_endpoint",
         {"type": str, "default": "", "help": "Endpoint URL of Azure OpenAI service. Only require when use AOAI."}),
        ("--azure_deployment_name",
         {"type": str, "default": "", "help": "Deployment of Azure OpenAI service. Only require when use AOAI."}),
    ]
    for argument, kwargs in arguments:
        parser.add_argument(argument, **kwargs)
    options = parser.parse_args()

    OPENAI_API_KEY = options.openai_key
    if not OPENAI_API_KEY:
        raise Exception("Please provide your OpenAI API key")

    return options

def check_file_path(file_path: Path):
    """
    Ensure file extension is in ALLOWED_FILE_TYPES or is a URL.
    If file ends with _translated.txt or _bilingual.txt, skip it.
    If there is any txt file ending with _translated.txt or _bilingual.txt, skip it.
    """
    if not file_path.suffix.lower() in ALLOWED_FILE_TYPES :
        print(f"File extension {file_path.suffix} is not allowed.")
        raise Exception("Please use a pdf file")

    if file_path.stem.endswith("_translated"):
        print(
            f"You already have a translated file for {file_path}, skipping...")
        return False

    if file_path.with_name(f"{file_path.stem}_translated.txt").exists():
        print(
            f"You already have a translated file for {file_path}, skipping...")
        return False

    return True

def translate_pdf_file(input_path, options):
    print(f"start translate {input_path}")
    if not check_file_path(input_path):
        return
    start_index = 0
    end_index = 1
    origin_text_list=[]
    with pdfplumber.open("lauterbach_demo.pdf") as pdf:
        # range(start_index, end_index, step)
        for i in range(start_index, end_index, 1):
            origin_text_list.append(pdf.pages[i].extract_text())

    translated_text_list = translate_text_file(origin_text_list, options)
    # translated_text_list = origin_text_list
    trans_file_path = input_path.with_name(f"{input_path.stem}_translated.txt")
    print(f"translate done, writing result in {trans_file_path}")
    with open(trans_file_path, "w", encoding='utf-8') as f:
        for text in translated_text_list:
            f.write(text)

def main():
    """Main function"""
    options = parse_arguments()
    input_path = Path(options.input_path)
    if not input_path.is_file():
        print("please input absolute path")
        return
    translate_pdf_file(input_path, options)

if __name__ == "__main__":
    main()
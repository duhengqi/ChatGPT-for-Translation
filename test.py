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
from tqdm import tqdm
from utils.bilingual_txt_to_docx import create_bilingual_docx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff
from concurrent.futures import as_completed

ALLOWED_FILE_TYPES = [
    ".txt",
    ".md",
    ".rtf",
    ".html",
    ".pdf",
]

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def translate(key, target_language, text, use_azure=False, api_base="", deployment_name="", options=None):
    client = OpenAI(
      api_key="sk-R5VhE7pR88Dm0xZmMAl17NtvKJgRbuB2NDbXp8hKR2hxUeOv",
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



def remove_empty_paragraphs(text):
    # Split the text into paragraphs
    if isinstance(text, str):
        text = text.split('\n')

    # Filter out empty paragraphs
    non_empty_paragraphs = filter(lambda p: p.strip() != '', text)

    # Join the non-empty paragraphs back into a string
    return '\n'.join(non_empty_paragraphs)



def translate_text_file(text_filepath_or_url, options):
    OPENAI_API_KEY = "sk-R5VhE7pR88Dm0xZmMAl17NtvKJgRbuB2NDbXp8hKR2hxUeOv"

    paragraphs = read_and_preprocess_data(text_filepath_or_url, options)

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


    translated_text = "\n".join(translated_paragraphs)

    # Output bilingual text file
    bilingual_text = "\n".join(f"{paragraph}\n{translation}"
                               for paragraph, translation in zip(
                                   paragraphs, translated_paragraphs))

    bilingual_text = remove_empty_paragraphs(bilingual_text)


    # Output translated text file
    # remove extra newlines
    translated_text = re.sub(r"\n{2,}", "\n", translated_text)

    translated_text = remove_empty_paragraphs(translated_text)
    output_file_translated = f"{Path(text_filepath_or_url).parent}/{Path(text_filepath_or_url).stem}_translated.txt"
    with open(output_file_translated, "w", encoding="utf-8") as f:
        f.write(translated_text)
        print(f"Translated text saved to {f.name}.")



def download_html(url):
    response = requests.get(url)
    return response.text


from utils.parse_pdfs.parse_tei_xml import extract_paper_info
from pathlib import Path
import trafilatura

def read_and_preprocess_data(text_filepath_or_url, options):
    with open(text_filepath_or_url, "r", encoding='utf-8') as f:
        text = f.read()
        if text_filepath_or_url.endswith('.html'):
            # extract text from HTML file
            print("Extracting text from HTML file...")
            text = trafilatura.extract(text)
            # write to a txt file ended with "_extracted"
            with open(
                    f"{Path(text_filepath_or_url).parent}/{Path(text_filepath_or_url).stem}_extracted.txt",
                    "w") as f:
                f.write(text)
                print(f"Extracted text saved to {f.name}.")
    paragraphs = [p.strip() for p in text.split("\n") if p.strip() != ""]

    return paragraphs



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
    ]

    for argument, kwargs in arguments:
        parser.add_argument(argument, **kwargs)

    options = parser.parse_args()
    OPENAI_API_KEY = "sk-R5VhE7pR88Dm0xZmMAl17NtvKJgRbuB2NDbXp8hKR2hxUeOv"

    return options

def process_file(file_path, options):
    """Translate a single text file"""
    print(f"Translating {file_path}...")
    translate_text_file(str(file_path), options)


def process_folder(folder_path, options):
    """Translate all text files in a folder"""
    # if only_process_this_file_extension is set, only process files with this extension
    if options.only_process_this_file_extension:
        files_to_process = list(
            folder_path.rglob(f"*.{options.only_process_this_file_extension}"))
        print(
            f"Only processing files with extension {options.only_process_this_file_extension}"
        )
        print(f"Found {len(files_to_process)} files to process")
    else:
        files_to_process = list(folder_path.rglob("*"))
    total_files = len(files_to_process)
    for index, file_path in enumerate(files_to_process):
        if file_path.is_file() and file_path.suffix.lower(
        ) in ALLOWED_FILE_TYPES:
            process_file(file_path, options)
        print(
            f"Processed file {index + 1} of {total_files}. Only {total_files - index - 1} files left to process."
        )


def main():
    """Main function"""
    options = parse_arguments()
    input_path = Path(options.input_path)
    if input_path.is_dir():
        # input path is a folder, scan and process all allowed file types
        process_folder(input_path, options)
    elif input_path.is_file:
        process_file(input_path, options)


if __name__ == "__main__":
    main()

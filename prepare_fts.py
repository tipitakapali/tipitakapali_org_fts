"""Tipitakapali.org FTS

- Assign each element k{number} id
A workaround for jumping to line in full text search.
Input: html files in https://tipitakapali.org/book/

"""

import json
import os
import re
from bs4 import BeautifulSoup
import shutil


def clean_tpo_html(text):
    text = text.replace("¶", " ")

    # ‘‘Idaṃ vatthu’’
    text = text.replace("‘‘", '"')
    text = text.replace("’’", '"')

    text = text.replace("“", '"')
    text = text.replace("”", '"')

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def copy_listed_files(filenames_txt, from_dir, to_dir):
    """Copy files listed in book.txt from from_dir to ./book directory"""
    # Create book directory if it doesn't exist
    if not os.path.exists(to_dir):
        os.makedirs(to_dir)

    # Read the list of files from book.txt
    with open(filenames_txt, "r", encoding="utf-8") as f:
        filenames = [line.strip() for line in f if line.strip()]

    print(f"Found {len(filenames)} files to copy")

    # Copy each file
    copied = 0
    for filename in filenames:
        src = os.path.join(from_dir, filename)
        dst = os.path.join(to_dir, filename)

        try:
            shutil.copy2(src, dst)
            copied += 1
            if copied % 50 == 0:  # Progress update every 50 files
                print(f"Copied {copied} files...")
        except FileNotFoundError:
            print(f"Warning: File not found - {filename}")
        except Exception as e:
            print(f"Error copying {filename}: {e}")

    print(f"\nCompleted: Copied {copied} out of {len(filenames)} files")


def extract_content(html_content):
    start_marker = "<!-- cst-content -->"
    end_marker = "<!-- cst-content ends -->"
    start_index = html_content.find(start_marker)
    if start_index == -1:
        return None, None, None
    end_index = html_content.find(end_marker, start_index + len(start_marker))
    if end_index == -1:
        # some files do not have ending "<!-- cst-content ends -->"
        end_marker = '<script src="../web/paliscriptconverter_edited.js" defer></script><script src="../web/handleClick.js" defer></script>'
    end_index = html_content.find(end_marker, start_index + len(start_marker))
    if end_index == -1:
        return None, None, None

    head = html_content[:start_index]
    extracted_content = html_content[start_index + len(start_marker) : end_index]
    if end_marker == "<!-- cst-content ends -->":
        tail = html_content[end_index + len(end_marker) :]
    else:
        tail = "\n\n" + html_content[end_index:]

    return head, extracted_content, tail


def add_id_attributes(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    element_id = 1
    # Iterate only through *direct* children of the root (what was parsed)
    for element in soup.find_all(recursive=False):
        # Only add name attribute if element text is not empty after stripping
        if element.get_text().strip():
            if element.get("id"):
                raise Exception(f"Error: Element already has ID '{element['id']}'.")
            element["id"] = f"k{element_id}"
            # anchor = soup.new_tag("a", id=f"k{element_id}")
            # element.insert_before(anchor)
            element_id += 1
    return str(soup)


def process_html_files(input_dir, output_dir, text_dir, add_id=True):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(text_dir):
        os.makedirs(text_dir)

    x = 0

    filenames = sorted([f for f in os.listdir(input_dir) if f.endswith(".html")])
    print("Total files:", len(filenames))

    for filename in filenames:
        input_filepath = os.path.join(input_dir, filename)
        output_filepath = os.path.join(output_dir, filename)
        text_filepath = os.path.join(text_dir, os.path.splitext(filename)[0] + ".txt")

        try:
            with open(input_filepath, "r", encoding="utf-8") as infile:
                content = infile.read()

            head, html_body, tail = extract_content(content)

            if not html_body:
                print("no marker", input_filepath)

            if html_body:
                x += 1
                if add_id:
                    modified_html = add_id_attributes(html_body)
                    full_output = (
                        head
                        + "<!-- cst-content -->"
                        + modified_html
                        + "\n"
                        + "<!-- cst-content ends -->"
                        + tail
                    )
                    with open(output_filepath, "w", encoding="utf-8") as outfile:
                        outfile.write(full_output)
                else:
                    modified_html = html_body

                # Extract text with element IDs
                soup = BeautifulSoup(modified_html, "html.parser")
                text_lines = []
                for element in soup.find_all(recursive=False):
                    element_id = element.get("id", "")
                    # Replace consecutive whitespace with a single space and preserve spaces
                    text = " ".join(element.get_text().split())
                    if text:
                        text = clean_tpo_html(text)
                        text_lines.append(f"@{element_id} {text}")

                # Save text content
                with open(text_filepath, "w", encoding="utf-8") as textfile:
                    text = "\n".join(text_lines)
                    textfile.write(text)

                print(f"{x}. Processed and saved: {filename}")
            else:
                print(f"No content found in: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")


def gen_title():
    with open("./data/xml_title.json", "r", encoding="utf-8") as f:
        xml_title = json.load(f)
        BOOK = {}
        for k, v in xml_title.items():
            if k.endswith(".toc.xml"):
                BOOK[k.replace(".toc.xml", "").replace(".xml", "")] = v
        with open("./data/fts_book_title.json", "w", encoding="utf-8") as b:
            json.dump(BOOK, b, ensure_ascii=False, indent=2)
        ##
        CHAPTER = {}
        for k, v in xml_title.items():
            if not k.endswith(".toc.xml"):
                CHAPTER[k.replace(".toc.xml", "").replace(".xml", "")] = v
        with open("./data/fts_chapter_title.json", "w", encoding="utf-8") as c:
            json.dump(CHAPTER, c, ensure_ascii=False, indent=2)
        ##
        ALL = {}
        for k, v in xml_title.items():
            ALL[k.replace(".toc.xml", "").replace(".xml", "")] = v
        with open("./data/fts_all_title.json", "w", encoding="utf-8") as a:
            json.dump(ALL, a, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    gen_title()

    # chapter_app = "chapter_flutter_si"

    # copy_listed_files(
    #     "./chapter_2700_for_all.txt",
    #     "/home/p/pDEV/tipitakapali/production/tipitakapali_org_flutter_min/assets/cstpali/chapter",
    #     chapter_app,
    # )

    # ##
    # input_directory = chapter_app
    # output_directory = f"{chapter_app}_html"
    # text_dir = f"{chapter_app}_txt"

    # process_html_files(input_directory, output_directory, text_dir, True)

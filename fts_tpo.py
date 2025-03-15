import json
import os
import re
import sqlite3


def add_tpo_sort(file_name):
    """this is for sorting results by tipitaka collections"""
    sortPrefix = ""
    names = file_name.split(".")
    firstNamePart = names[0].strip()
    if firstNamePart.startswith("vi"):
        sortPrefix = "00"
    elif firstNamePart.startswith("s01"):
        sortPrefix = "11"
    elif firstNamePart.startswith("s02"):
        sortPrefix = "22"
    elif firstNamePart.startswith("s03"):
        sortPrefix = "33"
    elif firstNamePart.startswith("s04"):
        sortPrefix = "44"
    elif firstNamePart.startswith("s05"):
        sortPrefix = "55"
    elif firstNamePart.startswith("abh"):
        sortPrefix = "66"
    elif firstNamePart.startswith("e"):
        sortPrefix = "77"

    # Find the last character in firstNamePart
    lastChar = firstNamePart.strip("0123456789").strip()[-1]
    if lastChar == "m":
        sortPrefix += "1"
    elif lastChar == "a":
        sortPrefix += "2"
    elif lastChar == "t":
        sortPrefix += "3"
    else:
        sortPrefix += "4"
    return sortPrefix


def fts_txt_indexer(in_dir: str):
    """Indexing notes:
    Do not use the entire file content as one string to index path, content
    Because of these reasons:
    1- fts5 snippet function will only see it as 1 fragment
    2- the fts5 SORT BY path function will be much slower

    So avoid using this:
        tuble_list = [(path, entire_file_text)]
        c.executemany("INSERT INTO pn VALUES (?,?)", tuble_list)
    """

    db = f"{in_dir}.db"

    if os.path.isfile(db):
        os.remove(db)
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("CREATE VIRTUAL TABLE pn USING fts5(path, cont)")

    # if text has vol1 or vol2, ignore its entire volume
    vols = sorted(
        [f.split(".vol", 1)[0] + ".txt" for f in os.listdir(in_dir) if ".vol" in f]
    )
    duplicated_books = list(set(vols))
    print("Duplicated books:", duplicated_books)

    filenames = sorted(
        [
            f
            for f in os.listdir(in_dir)
            if f.endswith(".txt") and f not in duplicated_books
        ]
    )

    print("Total files to index", len(filenames))
    n = 0
    with open("./data/fts_chapter_title.json", "r", encoding="utf-8") as f:
        chapter_title_json = json.load(f)

    for filename in filenames:
        file_key = filename[0:-4]  # remove .txt

        chapter_title = chapter_title_json.get(file_key, None)
        if not chapter_title:
            raise Exception(f"No chapter title found for {file_key}")

        sort_prefix = add_tpo_sort(file_key)

        full_path = os.path.join(in_dir, filename)
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        pat_cont_tubple_list = []
        for line in lines:
            # only index line length >=3
            if not line.strip() or len(line.strip()) < 3:
                continue
            text = line.strip()
            k_id = re.match(r"^@k\d+", text).group()[1:]

            if not k_id:
                print(f"No k_id found in {filename} line: {line.strip()}")
                continue
            text = text[text.find(" ") + 1 :]
            path_id = sort_prefix + "@" + file_key + "@" + k_id
            pat_cont_tubple_list.append((path_id, text))

        c.executemany("INSERT INTO pn VALUES (?,?)", pat_cont_tubple_list)
        n += 1
        if n % 1000 == 0:
            print(str(n) + ". Indexed: " + filename)

    print("Optimizing the database...")
    c.execute("INSERT INTO pn(pn) VALUES('optimize')")
    conn.commit()
    conn.execute("PRAGMA optimize")
    conn.execute("REINDEX")
    conn.execute("VACUUM")
    conn.close()


if __name__ == "__main__":
    fts_txt_indexer("chapter_flutter_ro_txt")

import json
import os
import re
import sqlite3


def add_tpo_sort(file_name):
    """this workaround is for sorting results by tipitaka collections"""
    sortPrefix = ""
    names = file_name.split(".")
    firstNamePart = names[0].strip()

    # Find the last character in firstNamePart
    lastChar = firstNamePart.strip("0123456789").strip()[-1]

    # mula attha tika anna
    if lastChar == "m":
        sortPrefix = "1"
    elif lastChar == "a":
        sortPrefix = "2"
    elif lastChar == "t":
        sortPrefix = "3"
    else:
        sortPrefix = "4"

    if firstNamePart.startswith("vi"):
        sortPrefix += "1"
    elif firstNamePart.startswith("s01"):
        sortPrefix += "2"
    elif firstNamePart.startswith("s02"):
        sortPrefix += "3"
    elif firstNamePart.startswith("s03"):
        sortPrefix += "4"
    elif firstNamePart.startswith("s04"):
        sortPrefix += "5"
    elif firstNamePart.startswith("s05"):
        sortPrefix += "6"
    elif firstNamePart.startswith("abh"):
        sortPrefix += "7"
    elif firstNamePart.startswith("e"):
        sortPrefix += "8"

    return sortPrefix


def fts_txt_indexer(
    in_dir: str, ordered_filenames: str = "sortedByPitakaChapterFiles.txt"
):
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
    # c.execute("CREATE VIRTUAL TABLE pn USING fts5(path, cont)")
    c.execute("CREATE VIRTUAL TABLE pn USING fts5(path, cont, prefix=3)")

    # if text has vol1 or vol2, ignore its entire volume
    with open(ordered_filenames, "r", encoding="utf-8") as f:
        filenames = [line.strip() for line in f.readlines()]

    print(
        "Total files to index:",
        len(filenames),
        "\nStart file",
        filenames[0],
        "...Last file:",
        filenames[-1],
    )
    n = 0
    with open("./data/fts_chapter_title.json", "r", encoding="utf-8") as f:
        chapter_title_json = json.load(f)

    for filename in filenames:
        file_key = filename[0:-5]  # remove .html

        # check has title or not only, title json will be filled in  the server
        chapter_title = chapter_title_json.get(file_key, None)
        if not chapter_title:
            raise Exception(f"No chapter title found for {file_key}")

        sort_prefix = add_tpo_sort(file_key)
        full_path = os.path.join(in_dir, f"{file_key}.txt")
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        pat_cont_tubple_list = []
        for line in lines:
            if not line.strip():
                continue
            if len(line.strip()) < 3:
                raise Exception(f"{line} line lengh <3 in {file_key}")

            text = line.strip()
            k_id = re.match(r"^@k\d+", text).group()[1:]

            if not k_id:
                print(f"No k_id found in {filename} line: {line.strip()}")
                continue
            # @k95 Tikatikañceva dukadukañca
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
    fts_txt_indexer("chapter_web_ro_txt", "sortedByPitakaChapterFiles.txt")

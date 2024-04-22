import os
import re


def assemble(files: list[str]) -> dict:
    sequenced_files = []
    matched_files = []
    for f in files:
        head, tail = os.path.splitext(f)
        matches = re.findall(r'\d+$', head)
        if matches:
            sequenced_files.append(f)
            matched_files.append(head.replace(matches[0], ""))
    matched_files = list(set(matched_files))

    result = []
    for m in matched_files:
        # print()
        # print(sequenced_files.count(m))
        seq_info = {
            "name": m,
            "quantity": sequenced_files.count(m),
            "files": []
        }
        for sf in sequenced_files:
            head, tail = os.path.splitext(sf)
            if m in head:
                seq_info["files"].append(sf)
        result.append(seq_info)

    return result


SOURCE_DIR = "resources/private/plateMain/v000"
file_names = os.listdir(SOURCE_DIR)
file_count = len(file_names)

print(assemble(file_names))
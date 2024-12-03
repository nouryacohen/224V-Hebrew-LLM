
from pathlib import Path

def get_data_list():
    file_path = Path(__file__).parent / "one_thousand_common_words.txt"

    with open(file_path, 'r') as file:
        data_list = [line.strip() for line in file]

    return data_list


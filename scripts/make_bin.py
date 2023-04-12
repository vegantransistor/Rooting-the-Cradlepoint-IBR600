import regex as re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("csv_file", help="path to csv file")
parser.add_argument("output", help="output file name")
args = parser.parse_args()

try:
    with open(args.csv_file, "r") as f, open(args.output, "wb") as w:
        for line in f.read():
            line = re.sub(r'\"SPI\",|\s|\n|0x', '', line)
            w.write(bytes.fromhex(line))
except OSError as error:
    print(f"Could not read CSV and/or write to output file: {error}")

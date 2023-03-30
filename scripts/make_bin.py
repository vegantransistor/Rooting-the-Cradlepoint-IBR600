import regex as re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("csv_file", help="path to csv file")
parser.add_argument("output", help="filename for the result")
args = parser.parse_args()


with open(args.csv_file) as f:
    with open(args.output , "wb") as w:
        for line in f:
            line = re.sub(r'\"SPI\",|\s|\n|0x', '', line)
            w.write(bytes.fromhex(line))

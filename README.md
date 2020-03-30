# lds-item-parse

Customized version of NotAdam's [lds-item-parse](https://github.com/NotAdam/lds-item-parse) for [GarlandTools](https://github.com/ufx/GarlandTools) supplemental data.
It grabs Instance, Drop and Acquire data form ffxiv lodestone.

## Setup

Requires Python 3.

* `pip install -r requirements.txt`

## Usage

Just execute `parse-item-list.py` with your python 3 executable.
After it's done, it'll write the data to the lodestone-data.json and FFXIV Data - Items.tsv.

It uses lxml instead of beautifulsoup4 for better performance.
If you want to use beautifulsoup4, then use `bs4-parse-item-list.py` (You should install beautifulsoup4 individually, because `requirements.txt` does not contains it.).
from shared import *

def main():
    # Driver code
    with open(CELL_TYPES_IN_FTUS) as f:
        data = json.load(f)
        pprint(data)

if __name__ == "__main__":
    main()
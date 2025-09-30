from shared import *


def main():
    # Driver code
    with open(CELL_TYPES_IN_FTUS) as f:
        data = json.load(f)
        print(f"✅ Loaded {CELL_TYPES_IN_FTUS}")


if __name__ == "__main__":
    main()

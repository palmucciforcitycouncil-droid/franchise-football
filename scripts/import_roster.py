import argparse
from app.services.importer.ingest import cli_import_from_dir

def main():
    parser = argparse.ArgumentParser(description="Import roster from CSV directory.")
    parser.add_argument("--path", required=True, help="Directory with teams.csv, players.csv, depth_chart.csv")
    args = parser.parse_args()
    res = cli_import_from_dir(args.path)
    print(f"Import summary: {res}")

if __name__ == "__main__":
    main()

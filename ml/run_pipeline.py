"""End-to-end pipeline: download -> clean -> EDA -> train."""
from ml import download_data, eda, preprocess, train


def main() -> None:
    download_data.download()
    preprocess.run()
    eda.run()
    train.run()


if __name__ == "__main__":
    main()

import argparse
import datetime
import pathlib
from joblib import dump
import json
import os

from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegressionCV
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV
import numpy as np

from src.data_preparation.pipeline import run_pipeline


def prepare_data_for_training(final_df):
    final_df = final_df.sample(frac=1, random_state=42)
    X = final_df.drop("label", axis=1)
    y = final_df["label"]
    scaler = preprocessing.StandardScaler().fit(X)

    X_scaled = scaler.transform(X)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=1 / 3, random_state=42
    )
    return X_train, X_test, y_train, y_test, scaler


def parse_arguments():
    argument_parser = argparse.ArgumentParser()

    argument_parser.add_argument("--segmentation", type=str, default="otsu")
    argument_parser.add_argument("--descriptors_proportion", type=float, default=0.4)
    argument_parser.add_argument("--clustering_method", type=str, default="kmeans")
    argument_parser.add_argument("--n_clusters", type=int, default=25)
    argument_parser.add_argument("--classification_model", type=str, default="lr")
    argument_parser.add_argument("--n_data", type=int, default=10000)
    argument_parser.add_argument(
        "--no_clustering", dest="no_clustering", action=argparse.BooleanOptionalAction
    )
    argument_parser.set_defaults(no_clustering=False)
    argument_parser.add_argument(
        "--no_df", dest="no_df", action=argparse.BooleanOptionalAction
    )
    argument_parser.set_defaults(use_df=False)

    args = argument_parser.parse_args()
    return args


def show_params(params):
    print("\n")
    print("#######################")
    print("# Run with parameters #")
    print("#######################\n")
    for param in params:
        print(f"{param} = {params[param]}")

    print("\n")
    print("#######################")
    print("#  Start of the run   #")
    print("#######################\n")


def run_classification(X_train, y_train, model_name):
    if model_name == "lr":
        model = LogisticRegressionCV(max_iter=1000, Cs=20)
        model.fit(X_train, y_train)
    elif model_name == "svm":
        params = dict(
            C=np.linspace(1e-5, 10, num=10),
        )
        model = GridSearchCV(SVC(), params, verbose=3)
        model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_train, y_train, X_test, y_test):
    train_accuracy = model.score(X_train, y_train)
    test_accuracy = model.score(X_test, y_test)
    print("Train accuracy: ", train_accuracy)
    print("Test accuracy: ", test_accuracy)


def save_experiment(experiments_path, model, clustering_model, final_df, params, date):
    path = experiments_path / (date + f"_{params['classification_model']}")
    os.makedirs(path)

    params["images_path"] = params["images_path"].__str__()
    params["labels_path"] = params["labels_path"].__str__()
    params["models_path"] = params["models_path"].__str__()
    params["final_data_path"] = params["final_data_path"].__str__()

    with open(path / "params.json", "w") as file:
        json.dump(params, file)
    dump(model, path / "model.joblib")
    dump(clustering_model, path / "clustering_model.joblib")
    final_df.to_csv(path / "final_df.csv", index=False)


if __name__ == "__main__":
    CACHE_DATA_PATH = pathlib.Path("./data/cache/")
    INTERIM_DATA_PATH = pathlib.Path("./data/interim/")
    MODELS_PATH = pathlib.Path("./models/")
    EXPERIMENTS_PATH = pathlib.Path("./experiments/")

    args = parse_arguments()

    date = datetime.datetime.today().strftime("%m_%d_%H_%M_%S")

    params = dict(
        images_path=INTERIM_DATA_PATH / "images",
        labels_path=INTERIM_DATA_PATH / "labels.csv",
        models_path=MODELS_PATH,
        final_data_path=CACHE_DATA_PATH,
        segmentation=args.segmentation,
        descriptors_proportion=args.descriptors_proportion,
        clustering_method=args.clustering_method,
        n_clusters=args.n_clusters,
        do_clustering=not args.no_clustering,
        classification_model=args.classification_model,
        n_data=args.n_data,
        use_df=args.no_df,
        date=date,
    )

    show_params(params)

    final_df, clustering_model = run_pipeline(params)

    X_train, X_test, y_train, y_test, scaler = prepare_data_for_training(
        final_df.drop("path", axis=1)
    )

    model = run_classification(X_train, y_train, params["classification_model"])
    evaluate_model(model, X_train, y_train, X_test, y_test)

    save_experiment(EXPERIMENTS_PATH, model, clustering_model, final_df, params, date)

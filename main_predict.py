# main_predict.py

import pandas as pd
from src.models.predict import predict_burnout
from src.features.feature_engineering import load_processed_data


def get_sample_input():
    """
    Creates a sample input using training columns.
    This prevents column mismatch errors.
    """

    df = load_processed_data()

    # take one row as template
    sample_row = df.drop(columns=["burnout_label"]).iloc[0]

    return sample_row.to_dict()


def main():

    print("🔮 Running burnout prediction...")

    # get safe sample input
    input_data = get_sample_input()

    # make prediction
    prediction = predict_burnout(input_data)

    print(f"✅ Predicted Burnout Score: {prediction:.4f}")


if __name__ == "__main__":
    main()
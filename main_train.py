from src.data.preprocess import run_preprocessing
from src.features.feature_engineering import run_feature_engineering
from src.models.train_model import train_model
from src.models.evaluate_model import evaluate_model
from src.explainability.shap_explainer import generate_shap_plots


def main():

    print("🚀 Starting ML Training Pipeline...\n")

    # Step 1 — Data preprocessing
    print("🔹 Step 1: Preprocessing data...")
    run_preprocessing()

    # Step 2 — Feature engineering
    print("🔹 Step 2: Feature engineering...")
    run_feature_engineering()

    # Step 3 — Model training
    print("🔹 Step 3: Training model...")
    model, X_test, y_test = train_model()

    # Step 4 — Model evaluation
    print("🔹 Step 4: Evaluating model...")
    evaluate_model(model, X_test, y_test)

    # Step 5 — SHAP explainability
    print("🔹 Step 5: Generating SHAP plots...")
    generate_shap_plots(model, X_test)

    print("\n🎉 Training pipeline complete!")
    print("Model saved in: models/model.pkl")
    print("SHAP plots saved in: outputs/")


if __name__ == "__main__":
    main()
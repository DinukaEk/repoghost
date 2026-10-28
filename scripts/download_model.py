from ghostcore.model import MODEL_ID, load_model

if __name__ == "__main__":
    print(f"Downloading / loading {MODEL_ID}")
    model = load_model(offline=False)
    vector = model.encode(["A forgotten bug fix in an old commit"])
    print(f"Ready: produced embedding with {len(vector[0])} dimensions")

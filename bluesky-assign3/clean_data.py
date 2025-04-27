import pandas as pd

df = pd.read_csv("test-data/manual-label.csv")
df = df.drop_duplicates(subset="URL", keep="first").reset_index(drop=True)
df = df.drop(columns="Labels")
df = df.drop(columns="Checker")

# Combine manually added labels
def combine_extras(row):
    return [v for v in (row["Link"], row["Bot"]) if pd.notna(v) and v != ""]

df["Labels"] = df.apply(combine_extras, axis=1)
df = df.drop(columns=["Link", "Bot"])
print(len(df))
df.to_csv("test-data/labels-cleaned.csv", index=False)

train_df = df.sample(frac=0.6, random_state=42)
test_df = df.drop(train_df.index)
print(len(train_df), len(test_df))

train_df.to_csv("test-data/labels-cleaned-train.csv", index=False)
test_df.to_csv("test-data/labels-cleaned-test.csv", index=False)
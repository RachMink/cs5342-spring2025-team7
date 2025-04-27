import pandas as pd

df = pd.read_csv("test-data/input-posts-giveaway-train-labeled.csv")
df.columns = ["URL", "Labels", "extra1", "extra2"]
df = df.drop_duplicates(subset="URL", keep="first").reset_index(drop=True)
df = df.drop(columns="Labels")

# Combine manually added labels
def combine_extras(row):
    return [v for v in (row["extra1"], row["extra2"]) if pd.notna(v) and v != ""]

df["Labels"] = df.apply(combine_extras, axis=1)
df = df.drop(columns=["extra1", "extra2"])
print(len(df))
df.to_csv("test-data/input-posts-giveaway-train-cleaned.csv", index=False)
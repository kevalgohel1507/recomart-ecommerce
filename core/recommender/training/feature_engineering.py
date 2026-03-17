from scipy.sparse import csr_matrix


def create_matrix(df):

    user_codes = df["user_id"].astype("category")
    product_codes = df["product_id"].astype("category")

    matrix = csr_matrix(
        (df["score"], (user_codes.cat.codes, product_codes.cat.codes))
    )

    encoders = {
        "user_map": dict(enumerate(user_codes.cat.categories)),
        "product_map": dict(enumerate(product_codes.cat.categories)),
        "user_index": user_codes.cat.categories,
        "product_index": product_codes.cat.categories,
    }

    return matrix, encoders
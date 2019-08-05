def encode_params(data: dict):
    result = {}
    for k, vs in data.items():
        if vs is None:
            continue

        if hasattr(vs, "__iter__") and not isinstance(vs, str):
            vs = ",".join(v for v in vs if v is not None)
            if vs:
                result[k] = vs
        else:
            result[k] = vs

    return result

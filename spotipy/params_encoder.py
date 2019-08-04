def encode_params(data: dict):
    result = {}
    for k, vs in data.items():
        if isinstance(vs, str) or not hasattr(vs, "__iter__"):
            vs = [vs]
        vs = ",".join(v for v in vs if v is not None)

        result[k] = vs

    return result

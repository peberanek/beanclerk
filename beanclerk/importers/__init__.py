def prepare_meta(dict_: dict) -> dict:
    new_dict = {}
    for k, v in dict_.items():
        if not (v is None or v == ""):
            new_dict[k] = str(v)
    return new_dict

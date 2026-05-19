import jsons


class JsonUtil:
    @staticmethod
    def to_json(data_object) -> str:
        return jsons.dumps(data_object)

    @staticmethod
    def from_json(json_string: str, cls):
        return jsons.loads(json_string, cls)

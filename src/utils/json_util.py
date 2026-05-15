import jsons
class JsonUtil:
    @staticmethod
    def to_json(data_object) -> str:
        return jsons.dumps(data_object)

    @staticmethod
    def from_json(json_string: str, cls):
        return jsons.loads(json_string, cls)
    @staticmethod
    def to_json(data_object) -> str:
        return JsonUtil.to_json(data_object)

    @staticmethod
    def fromJson(json_string: str, cls):
        return JsonUtil.from_json(json_string, cls)

# backend/utils/custom_json_coder.py - CustomJsonCoder

import json
from fastapi_cache.coder import JsonCoder

class CustomJsonCoder(JsonCoder):
    """
    JsonCoder, который:
      - При записи в Redis отдаёт plain JSON-строку (str), так что с decode_responses=True всё ровно сохраняется/читается как str
      - При загрузке принимает и bytes, и str и всегда возвращает Python-объект
    """    
    def dump(self, value: any) -> any:
        return json.dumps(value, default=self.default)

    def load(self, value: any) -> any:
        text = value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else value
        return json.loads(text)

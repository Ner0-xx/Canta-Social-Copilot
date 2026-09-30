from typing import Any

from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION

PYDANTIC_VERSION_MINOR_TUPLE = tuple(int(x) for x in PYDANTIC_VERSION.split(".")[:2])
PYDANTIC_V2 = PYDANTIC_VERSION_MINOR_TUPLE[0] >= 2


def is_pydantic_v1_model_instance(obj: Any) -> bool:
    try:
        from pydantic import v1
    except ImportError:
        return False
    return isinstance(obj, v1.BaseModel)


def is_pydantic_v1_model_class(cls: Any) -> bool:
    try:
        from pydantic import v1
    except ImportError:
        return False
    return isinstance(cls, type) and issubclass(cls, v1.BaseModel)


def annotation_is_pydantic_v1(annotation: Any) -> bool:
    if is_pydantic_v1_model_class(annotation):
        return True
    return False


class FieldInfoCompatibility:
    @staticmethod
    def get_field_info(field_info: Any) -> Any:
        return field_info


class ModelFieldCompatibility:
    @staticmethod
    def create_model_field(*args: Any, **kwargs: Any) -> Any:
        return None

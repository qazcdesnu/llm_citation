
from langchain_core.messages.base import BaseMessage, BaseMessageChunk


class DoctorMessage(BaseMessage):
    example: bool = False

    type: Literal["doctor"] = "doctor"

    @classmethod
    def get_lc_namespace(cls) -> List[str]:
        """Get the namespace of the langchain object."""
        return ["langchain", "schema", "messages"]


DoctorMessage.update_forward_refs()


class DoctorMessageChunk(DoctorMessage, BaseMessageChunk):
    """A Human Message chunk."""

    type: Literal["DoctorMessageChunk"] = "DoctorMessageChunk"  # type: ignore[assignment] # noqa: E501

    @classmethod
    def get_lc_namespace(cls) -> List[str]:
        """Get the namespace of the langchain object."""
        return ["langchain", "schema", "messages"]

class PatientMessage(BaseMessage):
    example: bool = False

    type: Literal["patient"] = "patient"

    @classmethod
    def get_lc_namespace(cls) -> List[str]:
        """Get the namespace of the langchain object."""
        return ["langchain", "schema", "messages"]


PatientMessage.update_forward_refs()


class PatientMessageChunk(PatientMessage, BaseMessageChunk):

    type: Literal["PatientMessageChunk"] = "PatientMessageChunk"  # type: ignore[assignment] # noqa: E501

    @classmethod
    def get_lc_namespace(cls) -> List[str]:
        """Get the namespace of the langchain object."""
        return ["langchain", "schema", "messages"]


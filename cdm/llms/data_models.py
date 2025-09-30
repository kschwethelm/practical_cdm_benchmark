from enum import Enum

from pydantic import BaseModel


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    ERROR = "error"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str

    def to_dict(self):
        return {"role": self.role.value, "content": self.content}


class Chat(BaseModel):
    messages: list[ChatMessage] = []

    def add_message(self, role: MessageRole, text: str) -> None:
        message = ChatMessage(role=role, content=text)
        self.messages.append(message)

    def to_dict(self, return_parent_dict: bool = False) -> list[dict[str, str]]:
        messages = [message.to_dict() for message in self.messages]
        if return_parent_dict:
            return {"messages": messages}
        else:
            return messages

    @staticmethod
    def create_single_turn_chat(user_message: str, system_prompt: str = None):
        chat = Chat()
        if system_prompt:
            chat.add_message(MessageRole.SYSTEM, system_prompt)
        chat.add_message(MessageRole.USER, user_message)
        return chat


class TokenCounts(BaseModel):
    completion_token_count: int
    prompt_token_count: int


class LLMResponse(BaseModel):
    response_text: str
    finish_reason: FinishReason
    token_counts: TokenCounts

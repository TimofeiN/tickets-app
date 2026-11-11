from pydantic import BaseModel

from app.shared.enums import ReactionType


class SuggestionReactionRequest(BaseModel):
    reaction: ReactionType


class SuggestionReactionResponse(BaseModel):
    suggestion_id: str
    reaction: ReactionType
    likes: int
    dislikes: int

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GoogleSignInRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_token: str | None = None
    credential: str | None = Field(
        default=None,
        description="Alias used by Google Identity Services / @react-oauth/google",
    )

    @model_validator(mode="after")
    def require_non_empty_token(self) -> "GoogleSignInRequest":
        if not (self.id_token or "").strip() and not (self.credential or "").strip():
            raise ValueError("Provide a non-empty id_token or credential")
        return self

    def token(self) -> str:
        tid = (self.id_token or "").strip()
        if tid:
            return tid
        return (self.credential or "").strip()
